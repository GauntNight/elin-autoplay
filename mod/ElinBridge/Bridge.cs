// ElinBridge: a local-only (127.0.0.1) bridge between Elin and the autoplay agent.
// Protocol: one JSON object per line in, one JSON object per line out.
// Everything that touches the game runs on Unity's main thread (Update); the
// socket thread only queues requests and waits for the answer.
// Honest play: state reports only what the player could see on screen.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using BepInEx;
using HarmonyLib;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace ElinAutoplay
{
    [BepInPlugin("elin.autoplay.bridge", "ElinBridge", Version)]
    public class Bridge : BaseUnityPlugin
    {
        public const string Version = "0.37.2";
        public const int Port = 47323;

        class Request
        {
            public JObject cmd;
            public JObject reply;
            public readonly ManualResetEventSlim done = new ManualResetEventSlim();
            // Set by the socket thread once its client stopped waiting: Update then drops the
            // request instead of running it late (a timed-out click used to fire after a zone load).
            public volatile bool abandoned;
            // A deferred reply (wait, walkto): checked every frame until it returns non-null.
            public Func<JObject> pending;
            public Func<JObject> onTimeout;
            // 0.30.0: what to undo when the client went away mid-walk (a killed tool's walkto used
            // to run on to arrival or 180 s: the review of 2026-10-23); WalkTo sets StopWalk.
            public Action onAbandon;
            public int deadline;
            public int startFrame;
        }

        static readonly List<Request> deferred = new List<Request>();
        static Request current;
        static readonly List<string> patchErrors = new List<string>();

        static readonly ConcurrentQueue<Request> queue = new ConcurrentQueue<Request>();
        static BepInEx.Logging.ManualLogSource log;

        // Virtual input, applied right after the game reads the real devices.
        static EAction virtAction = EAction.None;
        static int virtActionFrames;
        static Vector2 virtAxis;
        static int virtAxisFrames;
        static int virtAnyKeyFrames;

        static List<Button> lastButtons = new List<Button>();

        // Frame at which to exit after a `quit` (0 = not quitting); set after a successful save.
        static int quitAt;

        void Awake()
        {
            log = Logger;
            autoloadPath = Path.Combine(Path.GetDirectoryName(typeof(Bridge).Assembly.Location) ?? ".", "autoload.txt");
            // The listener first (run 12 review): a patch that fails after a game update must not
            // take the whole bridge down; `ping` lists the patches that failed.
            new Thread(Serve) { IsBackground = true, Name = "ElinBridge" }.Start();
            log.LogInfo("ElinBridge " + Version + " listening on 127.0.0.1:" + Port);
            var h = new Harmony("elin.autoplay.bridge");
            TryPatch("EInput.Update", () =>
            {
                var update = typeof(EInput).GetMethod("Update", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic, null, Type.EmptyTypes, null);
                h.Patch(update, postfix: new HarmonyMethod(typeof(Bridge), nameof(AfterInputUpdate)));
            });
            TryPatch("EInput.IsAnyKeyDown", () => h.Patch(AccessTools.Method(typeof(EInput), "IsAnyKeyDown"), postfix: new HarmonyMethod(typeof(Bridge), nameof(AfterAnyKey))));
            // run 23: the sneak guard runs at the start of the PC's own turn, before ai.Tick() advances a
            // mining task and its witness roll (TryWitnessCrime in the task's onProgress), so it sees
            // the same positions the roll would (the per-frame check alone could be a turn late).
            TryPatch("Chara.Tick", () => h.Patch(AccessTools.Method(typeof(Chara), "Tick"), prefix: new HarmonyMethod(typeof(Bridge), nameof(BeforeCharaTick))));
            TryPatch("UIContextMenu.Show", () =>
            {
                foreach (var m in AccessTools.GetDeclaredMethods(typeof(UIContextMenu)).Where(m => m.Name == "Show"))
                    h.Patch(m, postfix: new HarmonyMethod(typeof(Bridge), nameof(AfterContextMenuShow)));
            });
        }

        static void TryPatch(string name, Action patch)
        {
            try { patch(); }
            catch (Exception e)
            {
                patchErrors.Add(name + ": " + e.Message);
                log.LogError("ElinBridge patch " + name + " failed: " + e.Message);
            }
        }

        static void AfterInputUpdate()
        {
            if (virtActionFrames > 0) { EInput.action = virtAction; virtActionFrames--; }
            if (virtAxisFrames > 0) { EInput.axis = virtAxis; virtAxisFrames--; }
        }

        static void BeforeCharaTick(Chara __instance)
        {
            if (sneakR > 0 && __instance.IsPC)
                try { SneakWatch(); } catch { }
            if (__instance.IsPC)
                try { StaminaWatch(); } catch { }
        }

        static void AfterAnyKey(ref bool __result)
        {
            if (virtAnyKeyFrames > 0) __result = true;
        }

        // A context menu closes when the real mouse isn't over it. One opened by a bridge command
        // (Bed Options, policies...) stays open until an entry is clicked or Cancel; menus the
        // user opens with the mouse are untouched.
        static int handling;

        static void AfterContextMenuShow(UIContextMenu __instance)
        {
            if (handling <= 0 || !__instance) return;
            __instance.hideOnMouseLeave = false;
        }

        void Update()
        {
            while (queue.TryDequeue(out var req))
            {
                if (req.abandoned) { try { req.onAbandon?.Invoke(); } catch { } req.done.Set(); continue; }
                handling++;
                current = req;
                try { req.reply = Handle(req.cmd); }
                catch (Exception e) { req.reply = Err(Describe(e)); }
                finally { handling--; current = null; }
                if (req.reply == null && req.pending != null) { req.startFrame = Time.frameCount; deferred.Add(req); continue; }
                req.done.Set();
            }
            for (int i = deferred.Count - 1; i >= 0; i--)
            {
                var req = deferred[i];
                if (req.abandoned) { deferred.RemoveAt(i); try { req.onAbandon?.Invoke(); } catch { } req.done.Set(); continue; }
                JObject reply = null;
                try
                {
                    reply = req.pending();
                    if (reply == null && Environment.TickCount - req.deadline >= 0)
                        reply = req.onTimeout != null ? req.onTimeout() : Err("timeout: the condition did not come true");
                }
                catch (Exception e) { reply = Err(Describe(e)); }
                if (reply == null) continue;
                if (reply["data"] is JObject d) d["frames"] = Time.frameCount - req.startFrame;
                req.reply = reply;
                deferred.RemoveAt(i);
                req.done.Set();
            }
            TryAutoload();
            try { SneakWatch(); } catch { }
            try { StaminaWatch(); } catch { }
            // The game's own exit, a moment after the reply has gone out; Application.Quit
            // only if the game's path has not ended the process five seconds later.
            if (quitAt > 0 && Time.frameCount == quitAt) EClass.core.Quit();
            if (quitAt > 0 && Time.frameCount == quitAt + 300) Application.Quit();
        }

        // One-shot autoload: Elin has no "continue" launch option (Core reads only LANG_, DEV,
        // UPDATE_LANG, NOMOD). The agent writes a save id into autoload.txt beside this DLL
        // before launching; once the title screen has settled, the bridge loads that LOCAL save
        // (same Load as the `load` op) and deletes the file. No file: the normal title screen.
        static string autoloadPath;
        static int titleSeenFrame = -1;

        static void TryAutoload()
        {
            try
            {
                if (autoloadPath == null || Time.frameCount % 30 != 0 || !File.Exists(autoloadPath)) return;  // 0.30.0: not every frame
                bool inGame = false;
                try { inGame = EClass.core.game != null && EClass.pc != null; } catch { }
                if (inGame) { File.Delete(autoloadPath); return; }
                bool title = EClass.ui && EClass.ui.layers.Any(l => l is LayerTitle);
                if (!title) { titleSeenFrame = -1; return; }
                if (titleSeenFrame < 0) { titleSeenFrame = Time.frameCount; return; }
                if (Time.frameCount - titleSeenFrame < 90) return;
                string id = File.ReadAllText(autoloadPath).Trim();
                File.Delete(autoloadPath);
                foreach (var l in EClass.ui.layers.ToList())
                    if (!(l is LayerTitle)) l.Close();
                log.LogInfo("ElinBridge autoload " + id + ": " + Load(id).ToString(Formatting.None));
            }
            catch (Exception e)
            {
                log.LogWarning("ElinBridge autoload failed: " + e.Message);
                try { File.Delete(autoloadPath); } catch { }
            }
        }

        void LateUpdate()
        {
            if (virtAnyKeyFrames > 0) virtAnyKeyFrames--;
        }

        // ---- socket thread ----

        static void Serve()
        {
            var listener = new TcpListener(IPAddress.Loopback, Port);
            try { listener.Start(); }
            catch (Exception e) { log.LogError("ElinBridge could not listen: " + e.Message); return; }
            while (true)
            {
                TcpClient client;
                try { client = listener.AcceptTcpClient(); }
                catch (Exception e) { log.LogWarning("ElinBridge accept: " + e.Message); continue; }
                // One thread per client (run 12 review): a tool holding its connection open no
                // longer blocks the tools it launches; the main-thread queue still serializes ops.
                new Thread(() => ServeClient(client)) { IsBackground = true, Name = "ElinBridge client" }.Start();
            }
        }

        static void ServeClient(TcpClient client)
        {
            var utf8 = new UTF8Encoding(false);
            try
            {
                using (client)
                using (var stream = client.GetStream())
                using (var reader = new StreamReader(stream, utf8))
                using (var writer = new StreamWriter(stream, utf8) { AutoFlush = true, NewLine = "\n" })
                {
                    string line;
                    while ((line = reader.ReadLine()) != null)
                    {
                        // 0.37.1 (before publishing the repo): the protocol is one JSON object a line, so
                        // anything else ends the connection. It used to answer "bad request" and read on,
                        // which let a web page reach this port: a POST's request line and headers failed,
                        // then a JSON line in its body ran as a command. HTTP never starts with '{'.
                        if (line.Length == 0 || line[0] != '{') break;
                        JObject reply;
                        try
                        {
                            var req = new Request { cmd = JObject.Parse(line) };
                            // a deferred op (wait, walkto) names its own timeout; others get 15 s
                            int ms = Math.Min(Math.Max((int?)req.cmd["timeout"] ?? 15000, 1000), 180000) + 1000;
                            queue.Enqueue(req);
                            // 0.30.0: wait in slices and watch the socket, so a client that died
                            // (a killed tool, Ctrl-C) abandons its request at once and its walk stops
                            int waited = 0;
                            bool gone = false;
                            while (!req.done.Wait(250))
                            {
                                waited += 250;
                                if (waited >= ms) break;
                                try { gone = client.Client.Poll(0, SelectMode.SelectRead) && client.Client.Available == 0; } catch { gone = true; }
                                if (gone) break;
                            }
                            if (req.done.IsSet) reply = req.reply;
                            else
                            {
                                req.abandoned = true;
                                if (gone) break;
                                reply = Err("timeout: the game's main thread did not answer in " + ms + " ms (the request was dropped, not run late)");
                            }
                        }
                        catch (Exception e) { reply = Err("bad request: " + e.Message); }
                        writer.WriteLine(reply.ToString(Formatting.None));
                    }
                }
            }
            catch (Exception e) { log.LogWarning("ElinBridge client: " + e.Message); }
        }

        // ---- commands (main thread) ----

        static JObject Handle(JObject cmd)
        {
            string op = (string)cmd["op"];
            int frames = (int?)cmd["frames"] ?? 1;
            // World actions do nothing while a dialog or pop-up is open, and that failed silently
            // (run 04). bridge.py used to send a `state` before every one of these to check; the
            // check is here now (run 12 review: half the round trips). A container or shop window
            // (LayerInventory) is fine: tools open those on purpose and close them themselves.
            // 0.30.0 (the review of 2026-10-23): one guard for every op that changes the world,
            // the inventory ops included (run 17 ate with a bandit's demand open through invdo),
            // plus an open context menu (not a layer: BlockingTop never saw it). force=1 bypasses.
            var busy = Busy(cmd, op);
            if (busy != null) return Err(busy);
            switch (op)
            {
                case "ping":
                    return Ok(new JObject { ["version"] = Version, ["frame"] = Time.frameCount, ["patchErrors"] = new JArray(patchErrors), ["deferred"] = deferred.Count });
                case "state":
                    return Ok(State());
                case "buttons":
                    return Ok(Buttons((bool?)cmd["all"] ?? false, (string)cmd["text"], (string)cmd["name"], (string)cmd["card"]));
                case "cells":
                    return Ok(new JObject { ["cells"] = new JArray(((JArray)cmd["cells"] ?? new JArray()).Select(q => CellInfo((int)q[0], (int)q[1])["data"])) });
                case "wait":
                    return WaitFor(cmd);
                case "walkto":
                    return WalkTo((int)cmd["x"], (int)cmd["z"], cmd);
                case "texts":
                    return Ok(Texts((bool?)cmd["all"] ?? false, (int?)cmd["max"] ?? 200));
                case "cancel":
                    return CancelTask();
                case "closetop":
                    return CloseTop();
                case "click":
                    return Expect(cmd) ?? Click((int)cmd["i"]);
                case "rclick":
                    return Expect(cmd) ?? RightClick((int)cmd["i"]);
                case "shiftclick":
                    return ShiftClick((int)cmd["i"]);
                case "drag":
                    return Drag((int)cmd["i"], (int)cmd["j"], cmd["n"] == null ? 0 : (int)cmd["n"]);
                case "actions":  // every EAction name the input layer knows (run 04: find the F5 sleep)
                    return Ok(new JObject { ["actions"] = new JArray(Enum.GetNames(typeof(EAction))) });
                case "altitude":
                    return Altitude(cmd["d"] == null ? 0 : (int)cmd["d"]);
                case "hover":
                    return Hover((int)cmd["i"]);
                case "tip":
                    return Ok(new JObject { ["texts"] = new JArray(TooltipTexts().Select(t => Trunc(Clean(t), 400))) });
                case "choose":
                    return Choose((int)cmd["i"]);
                case "act":
                    virtAction = (EAction)Enum.Parse(typeof(EAction), (string)cmd["action"], true);
                    virtActionFrames = frames;
                    return Ok(new JObject { ["queued"] = virtAction.ToString(), ["frames"] = frames });
                case "move":
                    virtAxis = Dir((string)cmd["dir"]);
                    virtAxisFrames = frames;
                    return Ok(new JObject { ["axis"] = $"{virtAxis.x},{virtAxis.y}", ["frames"] = frames });
                case "step":
                    virtAxis = StepAxis((int)cmd["dx"], (int)cmd["dz"]);
                    virtAxisFrames = 1;
                    return Ok(new JObject { ["axis"] = $"{virtAxis.x},{virtAxis.y}" });
                case "anykey":
                    virtAnyKeyFrames = Math.Max(frames, 2);
                    return Ok(new JObject { ["frames"] = virtAnyKeyFrames });
                case "map":
                    return Ok(MapGrid((int?)cmd["r"] ?? 8));
                case "inv":
                    return Ok(Inventory());
                case "goto":
                    return Goto((int)cmd["x"], (int)cmd["z"]);
                case "quit":
                    return Quit();
                case "load":
                    return Load((string)cmd["id"]);
                case "acts":
                    return Acts((int)cmd["dx"], (int)cmd["dz"], (string)cmd["mode"] ?? "all");
                case "pick":  // 0.35.0 (run 31): a loose thing underfoot by uid (twinkled medals)
                    return PickUp((int)cmd["uid"]);
                case "do":
                    return DoAct((int)cmd["i"], (bool?)cmd["force"] ?? false);
                case "invacts":
                    return InvActs((int)cmd["i"]);
                case "invdo":
                    return InvDo((int)cmd["i"], cmd);
                case "winbtn":
                    return WinButton((string)cmd["name"]);
                case "boxcfg":
                    return BoxCfg((int?)cmd["priority"], (string)cmd["allow"], (bool?)cmd["noRotten"], (string)cmd["name"], (string)cmd["bag"]);
                case "cell":
                    return CellInfo((int)cmd["dx"], (int)cmd["dz"]);
                case "places":
                    return Places((int?)cmd["r"] ?? 12);
                case "terrain":
                    return Terrain((int?)cmd["r"] ?? 20, (string)cmd["want"], (int?)cmd["n"] ?? 12);
                case "sources":
                    return Sources((string)cmd["table"], (int?)cmd["offset"] ?? 0, (int?)cmd["limit"] ?? 400);
                case "find":
                    return FindOnMap((string)cmd["name"], (int?)cmd["r"] ?? 999, (int?)cmd["n"] ?? 20);
                case "power":
                    return Ok(Power());
                case "rooms":
                    return Ok(Rooms());
                case "stock":  // 0.33.0 (run 28, the user's stock caps): read-only
                    return Ok(Stock((int?)cmd["r"] ?? 999));
                case "genes":  // 0.37.0 (run 36, G38 M1): the allies' gene slots and feat points, read-only
                    return Ok(Genes());
                case "cast":  // 0.33.0 (run 28, G22: the user's tip, attack spells for exp)
                    return Cast((string)cmd["spell"], (int?)cmd["uid"]);
                case "props":  // 0.34.0 (run 30, G27): stealable NPC property on seen cells (Sleight of Hand marks)
                    return Props((int?)cmd["r"] ?? 12);
                case "skills":
                    return Ok(Skills());
                case "witness":
                    return Ok(Witness((int?)cmd["r"] ?? 6));
                case "sneak":
                    return Sneak((int?)cmd["r"]);
                case "spguard":  // run 25: the stamina floor; floor=-1 turns it off
                    return SpGuard((int?)cmd["floor"]);
                case "input":  // the open text dialog (Dialog.InputName: Change name): set the field and press Enter
                    {          // (the DialogInput prefab has no OK button: Enter is its only confirm, Dialog.OnUpdateInput)
                        var dlg = TopLayer() as Dialog;
                        if (dlg == null || dlg.input == null) return Err("no text dialog open (top: " + TopLayer()?.GetType().Name + ")");
                        dlg.input.Text = (string)cmd["text"] ?? "";
                        var text = dlg.input.Text;
                        if ((bool?)cmd["enter"] ?? true) dlg.OnEnterInput();
                        return Ok(new JObject { ["text"] = text });
                    }
                case "menu":  // 0.30.0: the open context menu (Bed Options, the System menu, poppers): list, press, close
                    return Menu((int?)cmd["i"], (string)cmd["text"], (bool?)cmd["close"] ?? false);
                case "autocombat":
                    return AutoCombat((int)cmd["uid"], (string)cmd["tactics"]);
                case "abortcombat":
                    return Ok(new JObject { ["aborted"] = EClass.player.TryAbortAutoCombat() });
                case "ride":  // 0.31.6: mount a party member (the Ride ability's target click), or off=1
                    return Ride((int?)cmd["uid"], (bool?)cmd["off"] ?? false);
                default:
                    return Err("unknown op: " + op);
            }
        }

        static Vector2 Dir(string d)
        {
            switch ((d ?? "").ToLowerInvariant())
            {
                case "n": case "up": return new Vector2(0, 1);
                case "s": case "down": return new Vector2(0, -1);
                case "w": case "left": return new Vector2(-1, 0);
                case "e": case "right": return new Vector2(1, 0);
                case "nw": case "upleft": return new Vector2(-1, 1);
                case "ne": case "upright": return new Vector2(1, 1);
                case "sw": case "downleft": return new Vector2(-1, -1);
                case "se": case "downright": return new Vector2(1, -1);
                default: throw new ArgumentException("dir must be n/s/e/w/ne/nw/se/sw");
            }
        }

        // Map deltas -> screen axis. The view is isometric: screen east is (+1,+1) on the map
        // (measured 2026-10-15: n=(-1,+1) ne=(0,+1) e=(+1,+1) se=(+1,0) s=(+1,-1) sw=(0,-1)
        // w=(-1,-1) nw=(-1,0)).
        static Vector2 StepAxis(int dx, int dz)
        {
            dx = Math.Sign(dx); dz = Math.Sign(dz);
            if (dx == 0 && dz == 0) throw new ArgumentException("step needs a non-zero dx or dz");
            return new Vector2(Math.Sign(dx + dz), Math.Sign(dz - dx));
        }

        static Cell CellAt(int x, int z)
        {
            var cells = EClass._map.cells;
            if (x < 0 || z < 0 || x >= cells.GetLength(0) || z >= cells.GetLength(1)) return null;
            return cells[x, z];
        }

        // Run 19 (death by drowning in Port Kapul): the game's own pathing swims through deep water,
        // where every step and turn suffocates (Cell.CanSuffocate). The first such cell on the
        // character's planned path (Chara.path: nodes[nodeIndex] is the next step, nodes[0] the
        // destination), or null.
        // 0.30.0: the current cell is reported as state.pc.inWater instead (with "(here)" every walk
        // out of the water stopped on its first frame); nothing is reported for a water breather.
        static string PathWater(Chara p)
        {
            try
            {
                if (BreathesWater(p)) return null;
                var path = p.path;
                if (p.HasNoGoal || path == null || path.state != PathProgress.State.PathReady || path.nodes == null) return null;
                for (int i = Math.Min(path.nodeIndex, path.nodes.Count - 1); i >= 0; i--)
                {
                    var n = path.nodes[i];
                    if (n.X == p.pos.x && n.Z == p.pos.z) continue;
                    var c = CellAt(n.X, n.Z);
                    if (c != null && c.CanSuffocate()) return $"{n.X},{n.Z}";
                }
            }
            catch { }
            return null;
        }

        // The first deep-water cell on the path the game would take from here to (x, z), or null:
        // asked before the walk starts (AI_Goto takes its first step in the frame it gets its path,
        // so the per-frame scan can be one step late). RequestPathImmediate fills the manager's
        // scratch progress, not the character's own path.
        static string WaterOnWay(Chara p, int x, int z)
        {
            try
            {
                if (BreathesWater(p)) return null;
                var pp = PathManager.Instance.RequestPathImmediate(p.pos, new Point(x, z), p, PathManager.MoveType.Default, -1, 0);
                if (pp == null || pp.state != PathProgress.State.PathReady || pp.nodes == null) return null;
                foreach (var n in pp.nodes)
                {
                    if (n.X == p.pos.x && n.Z == p.pos.z) continue;
                    var c = CellAt(n.X, n.Z);
                    if (c != null && c.CanSuffocate()) return $"{n.X},{n.Z}";
                }
            }
            catch { }
            return null;
        }

        // Honest play: an unidentified item's id would reveal what it is (run 04: a "cloudy potion"
        // carried the id of cure minor wound), so it reads "unidentified" until the player knows.
        static string PlayerId(Thing t) => t.IsIdentified ? t.id : "unidentified";

        static JObject ThingInfo(Thing t, int dx, int dz) => new JObject
        {
            ["name"] = Clean(t.Name),
            ["id"] = PlayerId(t),
            ["uid"] = t.uid,
            ["num"] = t.Num,
            ["dx"] = dx,
            ["dz"] = dz,
            ["installed"] = t.IsInstalled,
        };

        // Things on explored cells near the player, nearest first.
        static JArray NearbyThings(int r, int cap)
        {
            var pc = EClass.pc;
            var found = new List<(int d, JObject o)>();
            for (int dx = -r; dx <= r; dx++)
                for (int dz = -r; dz <= r; dz++)
                {
                    var c = CellAt(pc.pos.x + dx, pc.pos.z + dz);
                    if (c == null || !c.isSeen) continue;
                    var things = c.Things;
                    if (things == null) continue;
                    foreach (var t in things) found.Add((Math.Max(Math.Abs(dx), Math.Abs(dz)), ThingInfo(t, dx, dz)));
                }
            return new JArray(found.OrderBy(f => f.d).Take(cap).Select(f => f.o));
        }

        static JObject MapGrid(int r)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var visible = new Dictionary<(int, int), char>();
            foreach (var c in EClass._map.charas)
            {
                if (c == pc || c.isDead || !pc.CanSee(c)) continue;
                visible[(c.pos.x, c.pos.z)] = c.IsHostile() ? 'E' : c.IsPCParty ? 'p' : 'n';
            }
            var rows = new JArray();
            for (int z = pc.pos.z + r; z >= pc.pos.z - r; z--)
            {
                var sb = new StringBuilder();
                for (int x = pc.pos.x - r; x <= pc.pos.x + r; x++)
                {
                    var c = CellAt(x, z);
                    char ch;
                    if (c == null) ch = 'X';
                    else if (x == pc.pos.x && z == pc.pos.z) ch = '@';
                    else if (visible.TryGetValue((x, z), out var v)) ch = v;
                    else if (!c.isSeen) ch = ' ';
                    else if (c.HasStairs) ch = '>';
                    else if (c.IsDeepWater || c.IsTopWater) ch = '~';
                    else if (c.HasBlock && c.IsBlocked) ch = '#';
                    else if (c.HasObj && c.IsBlocked) ch = 'T';
                    else if (c.IsBlocked) ch = '#';
                    else if (c.Things != null && c.Things.Count > 0) ch = '*';
                    else if (c.HasObj) ch = '"';
                    else ch = '.';
                    sb.Append(ch);
                }
                rows.Add(sb.ToString());
            }
            return new JObject
            {
                ["origin"] = $"top-left is x={pc.pos.x - r}, z={pc.pos.z + r}; x grows right, z grows up",
                ["legend"] = "@ you, E hostile, p party, n other creature, > stairs, ~ water, # wall/blocked, T blocking object (tree, rock), * item, \" plant/small object, . floor, blank unexplored, X off-map",
                ["screen"] = "+x is screen south-east, +z is screen north-east",
                ["rows"] = rows,
            };
        }

        static JObject Inventory()
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            return new JObject
            {
                ["items"] = new JArray(pc.things.Select(t => new JObject
                {
                    ["name"] = Clean(t.Name),
                    ["id"] = PlayerId(t),
                    ["uid"] = t.uid,
                    ["num"] = t.Num,
                    ["equipped"] = t.isEquipped,
                    // what the tooltip and a guard's dialog tell the player (run 07, G8): a lost purse
                    // handed to a guard is Karma +5; opening its lock is Karma -8
                    ["lostProperty"] = t.isLostProperty,
                    ["lockLv"] = t.c_lockLv,
                })),
            };
        }

        // The fighting numbers the game itself shows the player: the character sheet (DV/PV,
        // attributes, skills, resistances) and the item tooltips' attack evaluations, computed by
        // the game's own AttackProcess.Prepare (dice, multiplier, hit, penetration), for me and
        // each party member. Foes get nothing here: their stats aren't on screen (state gives
        // their level and HP%), so their danger is learned from logged fights instead.
        static JObject Power()
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var party = new JArray();
            foreach (var c in pc.party.members)
            {
                var o = CharaPower(c);
                if (c == pc)
                {
                    // Ranged and thrown options in the pack (their tooltips show an evaluation too).
                    var extra = new JArray();
                    foreach (var t in pc.things)
                        if (!t.isEquipped && (t.IsRangedWeapon || t.IsThrownWeapon))
                            extra.Add(AttackEval(pc, t, 0, t.IsThrownWeapon, t.Num));
                    foreach (var a in extra) ((JArray)o["attacks"]).Add(a);
                }
                party.Add(o);
            }
            return new JObject
            {
                ["date"] = Safe(() => { var d = EClass.world.date; return $"{d.year}-{d.month:00}-{d.day:00} {d.hour:00}:{d.min:00}"; }),
                ["party"] = party,
            };
        }

        static JObject CharaPower(Chara c)
        {
            var attrs = new JObject();
            foreach (int id in new[] { 70, 71, 72, 73, 74, 75, 76, 77, 78, 79 })
                attrs[EClass.sources.elements.map[id].alias] = c.Evalue(id);
            var skills = new JObject();
            var res = new JObject();
            var spells = new JArray();
            foreach (var e in c.elements.dict.Values)
            {
                if (e.source.category == "skill" && e.source.categorySub == "combat" && e.Value != 0)
                    skills[e.source.alias] = e.Value;
                else if (e.source.category == "resist" && e.Value != 0)
                    res[e.source.alias] = e.Value;
                else if (e.source.category == "ability" && e.vPotential > 0)
                    spells.Add(new JObject { ["spell"] = e.source.alias, ["lv"] = e.Value, ["stock"] = e.vPotential, ["kind"] = e.source.categorySub });
            }
            int armorId = c.GetArmorSkill();
            var attacks = new JArray();
            int index = 0;
            foreach (var slot in c.body.slots)
            {
                if (slot.thing == null || slot.elementId != 35 || slot.thing.source.offense.Length < 2) continue;
                attacks.Add(AttackEval(c, slot.thing, index++, false, 1));
            }
            attacks.Add(AttackEval(c, null, 0, false, 1));  // martial arts, as the sheet lists it
            return new JObject
            {
                ["name"] = c.NameSimple,
                ["pc"] = c.IsPC,
                ["lv"] = c.LV,
                ["hp"] = c.hp,
                ["maxHp"] = c.MaxHP,
                ["mp"] = c.mana.value,
                ["maxMp"] = c.mana.max,
                ["speed"] = c.Speed,
                ["DV"] = c.DV,
                ["PV"] = c.PV,
                ["HIT"] = c.HIT,
                ["DMG"] = c.DMG,
                ["armorSkill"] = EClass.sources.elements.map[armorId].alias,
                ["armorSkillLv"] = c.Evalue(armorId),
                ["mainElement"] = c.MainElement != Element.Void ? c.MainElement.source.alias : null,
                ["attrs"] = attrs,
                ["skills"] = skills,
                ["resists"] = res,
                ["spells"] = spells,
                ["attacks"] = attacks,
            };
        }

        static JObject AttackEval(Chara c, Thing w, int index, bool isThrow, int num)
        {
            var ap = new AttackProcess();  // not AttackProcess.Current: a combat in progress keeps its own
            ap.Prepare(c, w, null, null, index, isThrow);
            var types = new JArray();
            if (w != null)
                foreach (var e in w.elements.dict.Values)
                    if (e.source.categorySub == "eleConvert" || e.source.categorySub == "eleAttack")
                        types.Add($"{e.source.alias} {e.Value}");
            return new JObject
            {
                ["weapon"] = w != null ? Clean(w.Name) : "martial arts",
                ["kind"] = w == null ? "martial" : isThrow ? "throw" : w.IsRangedWeapon ? "ranged" : "melee",
                ["num"] = num,
                ["eval"] = Clean(ap.GetText()),
                ["dNum"] = ap.dNum,
                ["dDim"] = ap.dDim,
                ["dBonus"] = ap.dBonus,
                ["ammo"] = ap.ammo != null ? Clean(ap.ammo.Name) : null,
                ["dNumAmmo"] = ap.dNumAmmo,
                ["dDimAmmo"] = ap.dDimAmmo,
                ["dBonusAmmo"] = ap.dBonusAmmo,
                ["dMulti"] = Math.Round(ap.dMulti, 3),
                ["toHit"] = ap.toHit,
                ["penetration"] = ap.penetration,
                ["attackType"] = ap.attackType.ToString(),
                ["skill"] = ap.weaponSkill?.source.alias,
                ["skillLv"] = ap.weaponSkill?.Value ?? 0,
                ["elements"] = types,
            };
        }

        static JObject Goto(int x, int z)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var c = CellAt(x, z);
            if (c == null) return Err("target is off the map");
            if (!c.isSeen) return Err("target cell is unexplored");
            pc.SetAIImmediate(new AI_Goto(new Point(x, z), 0));
            return Ok(new JObject { ["walking"] = $"{x},{z}", ["from"] = $"{pc.pos.x},{pc.pos.z}" });
        }

        // Save (when a game is loaded), then exit through the game's own Quit. Refuses to
        // quit if the save fails, so a quit never loses progress.
        static JObject Quit()
        {
            bool inGame = false;
            try { inGame = EClass.core.game != null && EClass.pc != null; } catch { }
            bool saved = false;
            if (inGame)
            {
                saved = EClass.game.Save(false, true);
                if (!saved) return Err("save failed: not quitting");
            }
            quitAt = Time.frameCount + 30;
            return Ok(new JObject { ["saved"] = saved, ["inGame"] = inGame, ["quitting"] = true });
        }

        // The game's own action list for a cell, built exactly as a click on it would be
        // (AM_Adv's planLeft/planAll): talk, pick up, open, read, attack... `do N` performs
        // item N as the context menu does, including the game's crime warning dialog.
        static ActPlan lastPlan;

        static JObject Acts(int dx, int dz, string mode)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            ActInput input;
            switch (mode)
            {
                case "all": input = ActInput.AllAction; break;
                case "left": input = ActInput.LeftMouse; break;
                case "key": input = ActInput.Key; break;
                case "right": input = ActInput.RightMouse; break; // uses the held item / hotbar tool
                default: return Err("mode must be all, left, key or right");
            }
            var target = new PointTarget { mouse = false };
            target.Update(new Point(pc.pos.x + dx, pc.pos.z + dz));
            var plan = new ActPlan { input = input };
            plan._Update(target);
            lastPlan = plan;
            return Ok(new JObject
            {
                ["cell"] = $"{pc.pos.x + dx},{pc.pos.z + dz}",
                ["acts"] = new JArray(plan.list.Select((it, i) => new JObject
                {
                    ["i"] = i,
                    ["text"] = Clean(it.GetTextContext(true)).Replace("\n", " "),
                    ["hint"] = Clean(it.GetText(true)).Replace("\n", " "), // the cursor hint: names an object target
                    ["act"] = it.act.GetType().Name,
                })),
            });
        }

        static JObject DoAct(int i, bool force = false)
        {
            if (lastPlan == null || i < 0 || i >= lastPlan.list.Count) return Err("no such act: call acts again");
            var it = lastPlan.list[i];
            // A party member on the cell puts its acts first, so an index read earlier can become Attack (the new-game
            // test, 0.37.2: my pet took a kick meant for "Pick all"). force=1 is for a deliberate hit on an ally.
            if (!force && it.tc != null && it.tc.isChara && it.tc.Chara.IsPCParty && !it.tc.Chara.IsPC && (it.act is ActMelee || it.act is ActKick))
                return Err("refused: act " + i + " is " + Clean(it.GetTextContext(true)) + " on a party member; use act.py by name (force=1 if you mean it)");
            lastPlan.performed = true;
            // Each `do` is a fresh click. AM_Adv.actCount counts repeats while the right button is
            // held and is only reset on a frame where it isn't; left stale, TaskPoint.Run reads
            // it as "right button held" and cancels the task (run 02: a door that never went on).
            AM_Adv.actCount = 0;
            if (it.Perform()) EClass.player.EndTurn();
            var text = Clean(it.GetTextContext(true));
            lastPlan = null;
            return Ok(new JObject { ["did"] = text });
        }

        // World map tiles within R: counts by biome/alias, and the nearest N tiles whose biome or alias
        // contains WANT (e.g. "beach": cacti and needles grow there), each with its road distance and
        // the danger a field there gets (RegionPoint.SetRegionPoint: road distance - 4, plus up to 10
        // for distance from home, plus the road distance past 20; capped at 100, then + 5).
        static JObject Terrain(int r, string want, int n)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            if (!EClass._zone.IsRegion) return Err("not on the world map");
            var em = EClass.scene.elomap;
            var home = EClass.game.StartZone;
            var counts = new Dictionary<string, int>();
            var cand = new List<(int d, int lx, int lz, EloMap.TileInfo t, string biome, string alias)>();
            for (int dz = -r; dz <= r; dz++)
                for (int dx = -r; dx <= r; dx++)
                {
                    int lx = pc.pos.x + dx, lz = pc.pos.z + dz;
                    EloMap.TileInfo t;
                    try { t = em.GetTileInfo(lx + em.minX, lz + em.minY); } catch { continue; }
                    if (t == null || t.source == null) continue;
                    string biome = string.IsNullOrEmpty(t.source.idBiome) ? "Plain" : t.source.idBiome;
                    string alias = t.source.alias ?? "";
                    string key = biome + "/" + alias;
                    counts[key] = counts.TryGetValue(key, out var c) ? c + 1 : 1;
                    if (string.IsNullOrEmpty(want)) continue;
                    if (biome.IndexOf(want, StringComparison.OrdinalIgnoreCase) < 0
                        && alias.IndexOf(want, StringComparison.OrdinalIgnoreCase) < 0) continue;
                    cand.Add((Math.Max(Math.Abs(dx), Math.Abs(dz)), lx, lz, t, biome, alias));
                }
            var hits = new JArray();
            foreach (var h in cand.OrderBy(h => h.d).Take(n))
            {
                int road = em.GetRoadDist(h.lx + em.minX, h.lz + em.minY);
                int fromHome = home == null ? 0 : new Point(h.lx, h.lz).Distance(home.mapX, home.mapY);
                int v = Mathf.Clamp(road - 4, 0, 200) + Mathf.Clamp(fromHome / 4, 0, 10);
                if (road > 20) v += road - 20;
                if (v >= 100) v = 100;
                hits.Add(new JObject
                {
                    ["dx"] = h.lx - pc.pos.x, ["dz"] = h.lz - pc.pos.z, ["dist"] = h.d,
                    ["biome"] = h.biome, ["alias"] = h.alias, ["road"] = road, ["danger"] = v + 5,
                    ["blocked"] = h.t.blocked || h.t.rock || h.t.sea, ["isRoad"] = h.t.isRoad,
                });
            }
            var here = new JObject();
            {
                int road = em.GetRoadDist(pc.pos.x + em.minX, pc.pos.z + em.minY);
                int fromHome = home == null ? 0 : pc.pos.Distance(home.mapX, home.mapY);
                int v = Mathf.Clamp(road - 4, 0, 200) + Mathf.Clamp(fromHome / 4, 0, 10);
                if (road > 20) v += road - 20;
                here["road"] = road; here["danger"] = Math.Min(v, 100) + 5;
            }
            return Ok(new JObject
            {
                ["me"] = $"{pc.pos.x},{pc.pos.z}", ["here"] = here,
                ["counts"] = JObject.FromObject(counts.OrderByDescending(kv => kv.Value).ToDictionary(kv => kv.Key, kv => kv.Value)),
                ["hits"] = hits,
            });
        }

        // World map: the places it draws near the player (within R tiles, about one screen) plus
        // every place already known (visited or revealed), with map deltas like `cell`/`acts`.
        static JObject Places(int r)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            if (!EClass._zone.IsRegion) return Err("not on the world map");
            var em = EClass.scene.elomap;
            var list = new List<(int d, JObject o)>();
            foreach (var s in EClass._zone.children)
            {
                if (s == null) continue;
                int dx = s.x - em.minX - pc.pos.x, dz = s.y - em.minY - pc.pos.z;
                int dist = Math.Max(Math.Abs(dx), Math.Abs(dz));
                if (!s.isKnown && dist > r) continue;
                list.Add((dist, new JObject
                {
                    ["name"] = Clean(s.NameWithDangerLevel),
                    ["id"] = s.id,
                    ["dx"] = dx,
                    ["dz"] = dz,
                    ["dist"] = dist,
                    ["known"] = s.isKnown,
                    ["danger"] = s.DangerLv,
                    ["town"] = s is Zone zz && zz.IsTown,
                }));
            }
            // Carried treasure maps: the dig spot, in the same frame as pc.pos (TaskDig.GetTreasureMap
            // compares the cell with GetDest(fix: true)). Reading the map computes the same point.
            var maps = new JArray();
            foreach (var t in pc.things.List(t => t.trait is TraitScrollMapTreasure))
            {
                var dest = (t.trait as TraitScrollMapTreasure).GetDest(fix: true);
                if (dest == null) continue;
                int dx = dest.x - pc.pos.x, dz = dest.z - pc.pos.z;
                maps.Add(new JObject { ["name"] = Clean(t.Name), ["lv"] = t.LV, ["dx"] = dx, ["dz"] = dz,
                    ["dist"] = Math.Max(Math.Abs(dx), Math.Abs(dz)), ["blessed"] = t.blessedState.ToString() });
            }
            return Ok(new JObject { ["me"] = $"{pc.pos.x},{pc.pos.z}", ["places"] = new JArray(list.OrderBy(t => t.d).Select(t => t.o)), ["treasure"] = maps });
        }

        // The game's own data tables (Core.Instance.sources) for the knowledge graph: every public,
        // serialized, plain field of each row, minus render and translation fields. Read-only.
        // `backers` lists real people, so it is never exported.
        static readonly HashSet<string> SkipTables = new HashSet<string> { "backers", "asset" };
        static readonly HashSet<string> SkipFields = new HashSet<string>
        {
            "tiles", "_tiles", "skins", "altTiles", "_altTiles", "anime", "shadow", "size", "light",
            "idShadow", "colorMod", "sort", "snowTile", "_idRenderData", "_tileType", "colorType",
            "idSound", "aliasPref", "W", "H", "multisize", "idActor", "idActorEx", "lightData",
            "idExtra", "tempChance", "idToggleExtra", "ignoreAltFix", "animeNoSync",
            "useAltColor", "useRandomColor", "useDyeColor", "_nameSearch", "_nameSearchJP",
        };

        static JObject Sources(string table, int offset, int limit)
        {
            var sm = Core.Instance.sources;
            var tables = typeof(SourceManager).GetFields(BindingFlags.Public | BindingFlags.Instance)
                .Where(f => !SkipTables.Contains(f.Name) && f.FieldType.GetField("rows") != null).ToList();
            System.Collections.IList Rows(FieldInfo f) => f.FieldType.GetField("rows").GetValue(f.GetValue(sm)) as System.Collections.IList;
            if (string.IsNullOrEmpty(table))
                return Ok(new JObject { ["tables"] = new JObject(tables.Select(f => new JProperty(f.Name, Rows(f)?.Count ?? 0))) });
            var tf = tables.FirstOrDefault(f => f.Name == table);
            if (tf == null) return Err("no table " + table);
            var rows = Rows(tf);
            var arr = new JArray();
            for (int i = offset; rows != null && i < Math.Min(rows.Count, offset + limit); i++)
            {
                var row = rows[i];
                var o = new JObject();
                foreach (var f in row.GetType().GetFields(BindingFlags.Public | BindingFlags.Instance))
                {
                    if (f.IsNotSerialized || SkipFields.Contains(f.Name) || f.Name.EndsWith("_JP") || f.Name.EndsWith("_L")) continue;
                    switch (f.GetValue(row))
                    {
                        case string v: if (v.Length > 0) o[f.Name] = v; break;
                        case int v: if (v != 0 || f.Name == "id") o[f.Name] = v; break;  // 0.30.0: a table's id-0 row keeps its id
                        case float v: if (v != 0) o[f.Name] = v; break;
                        case bool v: if (v) o[f.Name] = true; break;
                        case string[] v: if (v.Length > 0) o[f.Name] = new JArray(v); break;
                        case int[] v: if (v.Length > 0) o[f.Name] = new JArray(v); break;
                    }
                }
                arr.Add(o);
            }
            return Ok(new JObject { ["table"] = table, ["total"] = rows?.Count ?? 0, ["offset"] = offset, ["rows"] = arr });
        }

        // Search the explored map by name in one call: things and objects (trees, plants, rocks)
        // on seen cells, and creatures the player can see. Nearest first.
        static JObject FindOnMap(string name, int r, int n)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            name = (name ?? "").ToLowerInvariant();
            var cells = EClass._map.cells;
            int w = cells.GetLength(0), h = cells.GetLength(1);
            var hits = new List<(int d, JObject o)>();
            void Add(string kind, string nm, int x, int z, bool inst, bool? ripe = null, bool edge = false, string trait = null)
            {
                int dx = x - pc.pos.x, dz = z - pc.pos.z;
                int d = Math.Max(Math.Abs(dx), Math.Abs(dz));
                if (d > r || nm == null || !nm.ToLowerInvariant().Contains(name)) return;
                var o = new JObject
                {
                    ["kind"] = kind, ["name"] = nm, ["x"] = x, ["z"] = z,
                    ["dx"] = dx, ["dz"] = dz, ["dist"] = d, ["installed"] = inst,
                };
                if (ripe != null) o["ripe"] = ripe.Value;
                if (edge) o["edge"] = true;
                // 0.29.0 (run 20): the trait tells TraitStairsDown from TraitStairsUp (tools/ladder.py)
                if (trait != null) o["trait"] = trait;
                hits.Add((d, o));
            }
            for (int x = Math.Max(0, pc.pos.x - r); x < Math.Min(w, pc.pos.x + r + 1); x++)
                for (int z = Math.Max(0, pc.pos.z - r); z < Math.Min(h, pc.pos.z + r + 1); z++)
                {
                    var c = cells[x, z];
                    if (c == null || !c.isSeen) continue;
                    if (c.HasObj) Add("obj", Clean(c.GetObjName()), x, z, false, Ripe(c), c.outOfBounds);
                    if (c.Things != null)
                        foreach (var t in c.Things) Add("thing", Clean(t.Name), x, z, t.IsInstalled, null, c.outOfBounds, t.trait?.GetType().Name);
                }
            foreach (var ch in EClass._map.charas)
            {
                if (ch == pc || ch.isDead || !pc.CanSee(ch)) continue;
                Add("chara", Clean(ch.Name), ch.pos.x, ch.pos.z, false);
            }
            return Ok(new JObject
            {
                ["me"] = $"{pc.pos.x},{pc.pos.z}",
                ["count"] = hits.Count,
                ["hits"] = new JArray(hits.OrderBy(t => t.d).Take(n).Select(t => t.o)),
            });
        }

        // 0.33.0 (run 28, the user's stock caps): what the pack, its bags and every unlocked container
        // on an explored cell of this map hold (two levels down: a bag in a box), plus the shipping
        // chest's pending load. Read-only, and only what the player could see by opening each box:
        // a locked box (c_lockLv > 0) and NPC property report no contents. tools/stock.py counts it.
        static JObject Stock(int r)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            JArray Items(Card owner, int depth)
            {
                var arr = new JArray();
                foreach (var t in owner.things)
                {
                    var o = new JObject
                    {
                        ["name"] = Clean(t.Name), ["id"] = PlayerId(t), ["uid"] = t.uid, ["num"] = t.Num,
                    };
                    if (t.isEquipped) o["equipped"] = true;
                    if (t.c_charges != 0) o["charges"] = t.c_charges;
                    if (t.c_DNA != null) o["dna"] = DnaJson(t.c_DNA);  // 0.37.0 (run 36, G38 M1)
                    if (t.things.Count > 0 && depth < 2 && t.c_lockLv <= 0) o["items"] = Items(t, depth + 1);
                    arr.Add(o);
                }
                return arr;
            }
            JObject Box(Thing t)
            {
                var o = new JObject
                {
                    ["name"] = Clean(t.Name), ["uid"] = t.uid, ["x"] = t.pos.x, ["z"] = t.pos.z,
                    ["installed"] = t.IsInstalled, ["trait"] = t.trait?.GetType().Name,
                    ["slots"] = t.things.width * t.things.height, ["count"] = t.things.Count,
                };
                if (t.c_lockLv > 0) o["locked"] = t.c_lockLv;
                else if (t.isNPCProperty) o["property"] = true;
                else o["items"] = Items(t, 1);
                return o;
            }
            var boxes = new JArray();
            foreach (var t in EClass._map.things)
            {
                if (t.pos == null || !t.pos.IsValid || !(t.trait is TraitContainer || t.things.Count > 0)) continue;
                if (t.trait is TraitShippingChest) continue;  // its load is game.cards.container_shipping
                var c = t.pos.cell;
                if (c == null || !c.isSeen) continue;
                if (Math.Max(Math.Abs(t.pos.x - pc.pos.x), Math.Abs(t.pos.z - pc.pos.z)) > r) continue;
                boxes.Add(Box(t));
            }
            var ship = EClass.game.cards.container_shipping;
            return new JObject
            {
                ["zone"] = EClass._zone?.id,
                ["pack"] = Items(pc, 0),
                ["boxes"] = boxes,
                ["shipping"] = ship == null ? null : Items(ship, 1),
            };
        }

        // 0.37.0 (run 36, G38 M1): a gene's contents as its note shows them (DNA.WriteNote): type, cost in feat
        // points, gene slots, incubation hours (DNA.GetDurationHour) and each value with its element category
        // (slot, feat, ability: negative = party; else a skill or attribute bonus)
        static JObject DnaJson(DNA d)
        {
            var vals = new JArray();
            for (int i = 0; i + 1 < d.vals.Count; i += 2)
            {
                var row = EClass.sources.elements.map.TryGetValue(d.vals[i]);
                string name;
                try { name = Element.Create(d.vals[i], d.vals[i + 1]).Name; } catch { name = row?.alias; }
                vals.Add(new JObject
                {
                    ["id"] = d.vals[i], ["alias"] = row?.alias, ["name"] = Clean(name), ["cat"] = row?.category,
                    ["v"] = d.vals[i + 1],
                });
            }
            bool removable;
            try { removable = d.CanRemove(null); } catch { removable = true; }
            return new JObject
            {
                ["from"] = d.id, ["type"] = d.type.ToString(), ["cost"] = d.cost, ["slot"] = d.slot, ["lv"] = d.lv,
                ["hours"] = d.GetDurationHour(), ["vals"] = vals, ["removable"] = removable,
            };
        }

        // 0.37.0 (run 36, G38): the home branch's members the Gene Machine offers (TraitGeneMachine.OnUse's own
        // filter) and the party, with feat points, gene slots (Chara.MaxGeneSlot, CurrentGeneSlot), the genes they
        // carry, and for every gene in the pack and on this map's boxes whether it would take (InvOwnerGene's
        // checks: slots, a feat at its max, an action already known; plus the feat points to pay)
        static JObject Genes()
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var people = new List<Chara>();
            var branch = pc.homeBranch ?? EClass.Branch;
            if (branch != null)
                foreach (var m in branch.members)
                    if (!m.IsPC && m.memberType == FactionMemberType.Default && !people.Contains(m)) people.Add(m);
            foreach (var m in pc.party.members)
                if (!m.IsPC && !people.Contains(m)) people.Add(m);
            var dnas = new List<Thing>();
            void Collect(Card owner, int depth)
            {
                foreach (var t in owner.things)
                {
                    if (t.c_DNA != null) dnas.Add(t);
                    if (t.things.Count > 0 && depth < 3 && t.c_lockLv <= 0) Collect(t, depth + 1);
                }
            }
            Collect(pc, 0);
            foreach (var t in EClass._map.things)
                if (t.pos != null && t.pos.IsValid && t.things.Count > 0 && t.c_lockLv <= 0 && !t.isNPCProperty) Collect(t, 1);
            var arr = new JArray();
            foreach (var c in people)
            {
                var have = new JArray();
                if (c.c_genes != null) foreach (var d in c.c_genes.items) have.Add(DnaJson(d));
                int free = c.MaxGeneSlot - c.CurrentGeneSlot;
                var fits = new JArray();
                foreach (var t in dnas)
                {
                    var d = t.c_DNA;
                    if (d.type == DNA.Type.Inferior) continue;
                    int need = d.slot;
                    if (need > 1 && c.HasElement(1237)) need--;
                    int fp = d.cost * c.GeneCostMTP / 100;
                    string why = null;
                    if (need > free) why = "slots";
                    else if (fp > c.feat) why = "feat points";
                    else if (d.type != DNA.Type.Brain)
                    {
                        Element bad = null;
                        try { bad = d.GetInvalidFeat(c); } catch { }
                        if (bad != null) why = "feat at max: " + Clean(bad.Name);
                        else
                        {
                            try { bad = d.GetInvalidAction(c); } catch { }
                            if (bad != null) why = "knows: " + Clean(bad.Name);
                        }
                    }
                    else if (c.c_genes != null && c.c_genes.items.Exists(x => x.type == DNA.Type.Brain)) why = "has a brain";
                    fits.Add(new JObject { ["uid"] = t.uid, ["name"] = Clean(t.Name), ["fp"] = fp, ["slots"] = need, ["ok"] = why == null, ["why"] = why });
                }
                arr.Add(new JObject
                {
                    ["name"] = Clean(c.Name), ["uid"] = c.uid, ["lv"] = c.LV, ["race"] = c.race?.id, ["party"] = c.IsPCParty,
                    ["feat"] = c.feat, ["slotsMax"] = c.MaxGeneSlot, ["slotsUsed"] = c.CurrentGeneSlot,
                    ["inferior"] = c.c_genes?.inferior ?? 0, ["genes"] = have, ["incubating"] = c.GetCondition<ConSuspend>() != null,
                    ["fits"] = fits,
                });
            }
            return new JObject { ["members"] = arr, ["genesSeen"] = dnas.Count };
        }

        // 0.33.0 (run 28, G22): cast a spell from the ability list at a visible creature, by the game's own
        // ButtonAbility.TryUse path (pc.UseAbility, then EndTurn), which keeps every rule: cooldown, the
        // act's own ValidatePerform (range, line of sight), the spell stock, confusion and blindness. Refused
        // here first: no goal-free turn (an action running), a window or dialog open, the target out of
        // sight, and MP under the cost (the game would open its mana-overload warning and cast on HP).
        static JObject Cast(string spell, int? uid)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            if (string.IsNullOrEmpty(spell)) return Err("spell= the ability's alias (power.py lists them: arrow_Cold)");
            if (!pc.HasNoGoal) return Err("busy: " + pc.ai?.GetType().Name);
            if (EClass.ui.IsActive) return Err("a window or dialog is open");
            var e = pc.elements.GetElement(spell);
            if (e == null || e.act == null) return Err("no such ability on me: " + spell);
            var a = e.act;
            Card tc = pc;
            if (uid != null)
            {
                tc = EClass._map.charas.FirstOrDefault(ch => ch.uid == uid.Value && !ch.isDead);
                if (tc != null)
                {
                    if (!pc.CanSee((Chara)tc)) return Err("target not in sight");
                }
                else
                {
                    // 0.34.0 (run 30, G27): Sleight of Hand also takes NPC property things (AI_Steal.IsValidTC);
                    // only a thing on a seen cell, as the player could click it
                    var th = EClass._map.things.FirstOrDefault(t => t.uid == uid.Value);
                    if (th == null) return Err("no creature or thing with uid " + uid);
                    if (th.pos == null || th.pos.cell == null || !th.pos.cell.isSeen) return Err("thing not on a seen cell");
                    tc = th;
                }
            }
            var cost = a.GetCost(pc);
            int mp = pc.mana.value, stock = a.vPotential, hp = pc.hp;
            if (cost.type == Act.CostType.MP && pc.mana.value < cost.cost)
                return Err($"MP {pc.mana.value} under the cost {cost.cost}: the game would cast on HP");
            bool used = pc.UseAbility(a, tc, tc.pos);
            if (used && pc.HasNoGoal) EClass.player.EndTurn();
            return Ok(new JObject
            {
                ["cast"] = used, ["spell"] = spell, ["target"] = Clean(tc.Name),
                ["dist"] = pc.pos.Distance(tc.pos), ["cost"] = cost.cost,
                ["mp"] = $"{mp} -> {pc.mana.value}", ["stock"] = $"{stock} -> {a.vPotential}",
                ["hp"] = $"{hp} -> {pc.hp}",
            });
        }

        // 0.34.0 (run 30, G27 Thieves rank 1): the NPC property Sleight of Hand could take (AI_Steal.IsValidTC: NPC
        // property, CanBeStolen, unlocked) on seen cells within r, with its weight against the steal limit
        // (Pickpocket x 200 + STR x 100 + 1000), its sell price, and the guild contribution a stolen copy would pay
        // when sold (ShopTransaction: (int)sqrt(unit price) / 2 a unit; a member's stolen price is x100/(190 - 2 rank)).
        static JObject Props(int r)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            int limit = pc.Evalue(281) * 200 + pc.STR * 100 + 1000;
            var thief = Guild.Thief;
            int rank = thief.relation.rank;
            var list = new List<(int d, JObject o)>();
            foreach (var t in EClass._map.things)
            {
                if (t == null || t.pos == null || t.pos.cell == null || !t.pos.cell.isSeen) continue;
                if (!t.isNPCProperty || t.trait == null || !t.trait.CanBeStolen || t.c_lockLv > 0) continue;
                int d = pc.pos.Distance(t.pos);
                if (d > r) continue;
                int sell = t.GetPrice(CurrencyType.Money, true);
                int stolen = thief.IsMember ? sell * 100 / (190 - rank * 2) : sell;
                int contrib = ((int)Math.Sqrt(stolen) / 2) * Math.Max(1, t.Num);
                list.Add((d, new JObject
                {
                    ["uid"] = t.uid, ["name"] = Clean(t.Name), ["x"] = t.pos.x, ["z"] = t.pos.z, ["dist"] = d,
                    ["installed"] = t.IsInstalled, ["weight"] = t.ChildrenAndSelfWeight, ["liftable"] = t.ChildrenAndSelfWeight <= limit,
                    ["sell"] = sell, ["stolenSell"] = stolen, ["contribution"] = contrib, ["num"] = t.Num,
                }));
            }
            return Ok(new JObject
            {
                ["limit"] = limit, ["rank"] = rank, ["member"] = thief.IsMember,
                ["props"] = new JArray(list.OrderBy(x => x.d).Select(x => x.o)),
            });
        }

        // The map's rooms and lots (houses) as the game built them (RoomManager: Room.Refresh names a
        // room from its room board; RebuildLots merges rooms within 1 cell in the same board group),
        // and every installed thing on an explored cell with the room it stands in (G12, run 18:
        // tools/town.py). Read-only: dirty flags are reported, not refreshed.
        static JObject Rooms()
        {
            if (EClass.pc == null) throw new InvalidOperationException("not in game");
            var rm = EClass._map.rooms;
            var lots = rm.listLot;
            var rooms = new JArray();
            foreach (var r in rm.listRoom)
                rooms.Add(new JObject
                {
                    ["uid"] = r.uid, ["name"] = Clean(r.Name), ["plate"] = r.plate != null,
                    ["group"] = r.data.group, ["access"] = r.data.accessType.ToString(),
                    ["roof"] = r.roof, ["lot"] = lots.IndexOf(r.lot),
                    ["x"] = r.x, ["z"] = r.z, ["mx"] = r.mx, ["mz"] = r.mz, ["cells"] = r.points.Count,
                });
            var things = new JArray();
            foreach (var t in EClass._map.things)
            {
                if (!t.IsInstalled || t.pos == null || !t.pos.IsValid) continue;
                var c = t.pos.cell;
                if (c == null || !c.isSeen) continue;
                things.Add(new JObject
                {
                    ["id"] = t.id, ["name"] = Clean(t.Name), ["trait"] = t.trait.GetType().Name,
                    ["x"] = t.pos.x, ["z"] = t.pos.z, ["room"] = c.room?.uid ?? 0,
                    ["crafter"] = t.trait is TraitCrafter, ["bed"] = t.trait is TraitBed,
                    ["container"] = t.trait is TraitBaseContainer, ["door"] = t.trait is TraitDoor,
                });
            }
            return new JObject
            {
                ["zone"] = EClass._zone.ZoneFullName, ["dirtyRooms"] = rm.dirtyRooms, ["dirtyLots"] = rm.dirtyLots,
                ["lots"] = lots.Count, ["rooms"] = rooms, ["things"] = things,
            };
        }

        // A plant's crop is ready to pick (GrowSystem.CanHarvest: a harvest stage, not yet picked).
        // Harvesting an unripe crop destroys the plant (run 03: three berry bushes lost). Null when
        // the object doesn't grow.
        static bool? Ripe(Cell c)
        {
            if (!c.HasObj || c.sourceObj.growth == null) return null;
            try { return c.growth.CanHarvest(); } catch { return null; }
        }

        // What an explored cell holds: floor, block (wall), object (tree, plant, rock), things.
        // run 23: every skill the character sheet lists (power covers only the combat ones)
        static JObject Skills()
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var o = new JObject();
            foreach (var e in pc.elements.dict.Values.OrderBy(e => e.source.alias))
                if (e.source.category == "skill" && e.ValueWithoutLink != 0)
                    o[e.source.alias] = new JObject
                    {
                        ["lv"] = e.Value, ["base"] = e.ValueWithoutLink, ["name"] = Clean(e.Name),
                        ["exp"] = e.vExp, ["next"] = e.ExpToNext, ["potential"] = e.Potential,  // run 23: training rates
                    };
            // run 24: bought cure potions turned into negative ones (Chara.TryPoisonPotion: Ether Hand,
            // 1565) and rods lost charges (Mana Battery, 1564): the ether diseases, corruption (each 100
            // is one disease, Chara.ModCorruption) and the feats with the points to spend
            var ether = new JObject();
            var feats = new JObject();
            // run 35: a twisted-legs mutation (-5 speed) and a CHA drain (-4: the ally cap 3 -> 2) went unseen for a run;
            // mutations are their own category, and drains are negative temp elements (Chara.ModTempElement)
            var mutations = new JObject();
            foreach (var e in pc.elements.dict.Values.OrderBy(e => e.source.alias))
            {
                if (e.source.category == "ether" && e.Value != 0)
                    ether[e.source.alias] = new JObject { ["id"] = e.id, ["lv"] = e.Value, ["name"] = Clean(e.Name) };
                else if (e.source.category == "feat" && e.Value != 0)
                    feats[e.source.alias] = e.Value;
                else if (e.source.category == "mutation" && e.Value != 0)
                    mutations[e.source.alias] = new JObject
                    {
                        ["id"] = e.id, ["lv"] = e.Value, ["name"] = Clean(e.Name),
                        ["neg"] = e.source.tag != null && e.source.tag.Contains("neg"),
                    };
            }
            var drains = new JObject();
            if (pc.tempElements != null)
                foreach (var e in pc.tempElements.dict.Values)
                    if (e.vBase < 0)
                        drains[e.source.alias] = e.vBase;
            return new JObject
            {
                ["skills"] = o, ["ether"] = ether, ["corruption"] = pc.corruption,
                ["feats"] = feats, ["featPoints"] = pc.feat, ["mutations"] = mutations, ["drains"] = drains,
            };
        }

        // run 23 (G18, mining in a town): a hostile act is witnessed by a human within 4 cells with
        // line of sight to me (Point.ListWitnesses -> ListPointsInCircle(los: true)), 1 in 10 a progress
        // tick, and the witness calls the nearest guard. This lists the creatures I can see within r and
        // counts the cells in line of sight that I can't see (dark): a person could stand unseen there.
        // Point.ListWitnesses' crime rules without its one random skip (ConDim: half the time), and only
        // creatures I can see: line of sight within the circle, a human, fairy, god or mutant, not
        // suspended, paralysed, disabled, blind, confused, of my faction, or a hostile monster.
        static bool CouldWitness(Chara pc, Chara ch, int r)
        {
            if (ch == pc || ch.IsPC || !pc.CanSee(ch) || pc.pos.Distance(ch.pos) > r) return false;
            if (ch.conSuspend != null || ch.isParalyzed || ch.IsDisabled || !ch.CanWitness) return false;
            if (ch.isBlind || ch.isConfused || ch.IsPCFaction || ch.IsPCFactionMinion) return false;
            if (ch.OriginalHostility < Hostility.Neutral) return false;
            return Los.IsVisible(pc.pos, ch.pos);
        }

        // run 23 (G18): the sneak guard. While on (r > 0), a hostile task (TaskMine, TaskDig, a
        // Disassemble of property) in a lawful zone is cancelled at the start of my turn (and every
        // frame) when a creature that could witness it stands within r: the game rolls 1 in 10 a
        // progress tick for each witness in ListPointsInCircle(4), a strict circle (dx*dx + dz*dz < 16,
        // so Distance <= 3), and the witness calls the nearest guard (Lv40 cyber guards in Aquli Teola).
        // r = 3 is the game's own set; more is margin.
        static int sneakR;
        static string sneakStop;
        static int sneakStops;

        static void SneakWatch()
        {
            if (sneakR <= 0) return;
            var pc = EClass.pc;
            if (pc == null || pc.HasNoGoal || EClass._zone == null || !EClass._zone.HasLaw || EClass._zone.IsPCFaction) return;
            bool hostile = false;
            for (AIAct a = pc.ai; a != null; a = a.child) if (a.IsHostileAct) { hostile = true; break; }
            if (!hostile) return;
            var w = EClass._map.charas.Where(ch => CouldWitness(pc, ch, sneakR)).ToList();
            if (w.Count == 0) return;
            sneakStop = string.Join(", ", w.Select(ch => Clean(ch.NameSimple) + " d" + pc.pos.Distance(ch.pos)));
            sneakStops++;
            pc.ai.Cancel();
        }

        static JObject Sneak(int? r)
        {
            if (r != null) { sneakR = Math.Max(0, r.Value); sneakStop = null; sneakStops = 0; }
            return Ok(new JObject { ["r"] = sneakR, ["stops"] = sneakStops, ["lastStop"] = sneakStop });
        }

        // run 25: the stamina guard. A drag of 124 fibers onto the spinner's grid started one AI_UseCrafter
        // task that spun thread after thread while the tools watched only the AI state: SP 51 -> -19, the
        // HP drain of negative stamina took me to -5 ("You died from overwork", 594 orens). The rule
        // "negative SP costs HP" had no enforcement on a task the game runs by itself. While on
        // (spFloor >= 0; 3 by default, the lowest min_sp any tool uses), a work task (TaskMine, TaskDig,
        // TaskHarvest, TaskCut, TaskBuild, TaskPlow, TaskWater, AI_UseCrafter, AI_PracticeDummy, AI_Fish,
        // AI_Craft and every other Task*) is cancelled at the start of my turn and every frame once
        // stamina is at or under the floor. Sleep, eating, walking and combat are left alone (a sleep
        // starts at SP 0; combat is fight.py's floor). `spguard floor=N` reads and sets it.
        static int spFloor = 3;
        static string spStop;
        static int spStops;

        static bool IsWorkAct(AIAct a)
        {
            var n = a.GetType().Name;
            return n.StartsWith("Task") || n == "AI_UseCrafter" || n == "AI_PracticeDummy" || n == "AI_Fish" || n == "AI_Craft";
        }

        static void StaminaWatch()
        {
            if (spFloor < 0) return;
            var pc = EClass.pc;
            if (pc == null || pc.HasNoGoal || pc.stamina.value > spFloor) return;
            bool work = false;
            string what = null;
            for (AIAct a = pc.ai; a != null; a = a.child)
            {
                // Placing a held item costs no stamina: stopping it left a new character at SP 0 unable to set down
                // the workbench it needed for a bed, the only way to get stamina back (the new-game test, 0.37.2).
                if (a is TaskBuild b && b.useHeld) continue;
                if (IsWorkAct(a)) { work = true; what = a.GetType().Name; break; }
            }
            if (!work) return;
            spStop = what + " at SP " + pc.stamina.value + " (floor " + spFloor + ")";
            spStops++;
            pc.ai.Cancel();
        }

        static JObject SpGuard(int? floor)
        {
            if (floor != null) { spFloor = floor.Value; spStop = null; spStops = 0; }
            return Ok(new JObject { ["floor"] = spFloor, ["stops"] = spStops, ["lastStop"] = spStop });
        }

        static JObject Witness(int r)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var seen = new JArray();
            foreach (var ch in EClass._map.charas)
            {
                if (ch == pc || ch.IsPCParty || !pc.CanSee(ch)) continue;
                int d = pc.pos.Distance(ch.pos);
                if (d > r) continue;
                seen.Add(new JObject
                {
                    ["name"] = Clean(ch.NameSimple), ["id"] = ch.id, ["dist"] = d,
                    ["dx"] = ch.pos.x - pc.pos.x, ["dz"] = ch.pos.z - pc.pos.z,
                    ["witness"] = CouldWitness(pc, ch, r),
                    ["canWitness"] = ch.CanWitness, ["faction"] = ch.IsPCFaction || ch.IsPCFactionMinion,
                    ["guard"] = ch.trait is TraitGuard, ["sleeping"] = ch.HasCondition<ConSleep>(),
                    ["los"] = Los.IsVisible(pc.pos, ch.pos),
                });
            }
            int blind = 0;
            var blindCells = new JArray();
            foreach (var p in EClass._map.ListPointsInCircle(pc.pos, r, mustBeWalkable: true, los: true))
            {
                if (pc.fov != null && pc.fov.lastPoints.ContainsKey(p.index)) continue;
                blind++;
                if (blindCells.Count < 12) blindCells.Add($"{p.x - pc.pos.x},{p.z - pc.pos.z}");
            }
            return new JObject
            {
                ["me"] = $"{pc.pos.x},{pc.pos.z}", ["r"] = r, ["creatures"] = seen,
                ["blindCells"] = blind, ["blindSample"] = blindCells,
                ["zoneLaw"] = EClass._zone.HasLaw && !EClass._zone.IsPCFaction,
            };
        }

        static JObject CellInfo(int dx, int dz)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var c = CellAt(pc.pos.x + dx, pc.pos.z + dz);
            if (c == null) return Err("off the map");
            if (!c.isSeen) return Err("unexplored");
            return Ok(new JObject
            {
                ["cell"] = $"{pc.pos.x + dx},{pc.pos.z + dz}",
                ["floor"] = c.HasFloor ? Clean(c.sourceFloor.GetName()) : null,
                ["block"] = c.HasBlock ? Clean(c.sourceBlock.GetName()) : null,
                // run 23 (G18): what a dig or a mine yields and needs (BaseTaskHarvest: reqLv =
                // hardness + reqHarvest's level; MineFloor drops the recipe's ingredient in this material)
                ["floorMat"] = c.HasFloor ? c.matFloor.alias : null,
                ["floorHard"] = c.HasFloor ? (int?)c.matFloor.hardness : null,
                ["floorReq"] = c.HasFloor && c.sourceFloor.reqHarvest != null ? string.Join(",", c.sourceFloor.reqHarvest) : null,
                ["blockMat"] = c.HasBlock ? c.matBlock.alias : null,
                ["blockHard"] = c.HasBlock ? (int?)c.matBlock.hardness : null,
                ["blockReq"] = c.HasBlock && c.sourceBlock.reqHarvest != null ? string.Join(",", c.sourceBlock.reqHarvest) : null,
                // Walls are panels: blockDir 0/1 = the two axes, 2 = corner; crossWall flips it.
                ["blockDir"] = c.HasBlock ? (int?)c.blockDir : null,
                ["crossWall"] = c.HasBlock ? (bool?)c.crossWall : null,
                ["wall"] = c.HasBlock && c.sourceBlock.tileType.IsWallOrFence,
                ["door"] = c.hasDoor,
                ["edge"] = c.outOfBounds,
                ["obj"] = c.HasObj ? Clean(c.GetObjName()) : null,
                ["harvestable"] = c.HasObj && c.CanHarvest(),
                ["ripe"] = Ripe(c),
                ["growStage"] = c.HasObj && c.sourceObj.growth != null ? (int?)c.growth.stage.idx : null,
                // run 12: a watered field cell shows darker; water.py skips it (a second "Water"
                // on a watered cell spends a charge and SP for nothing, the user saw it)
                ["watered"] = c.isWatered,
                ["blocked"] = c.IsBlocked,
                ["water"] = c.IsDeepWater || c.IsTopWater,
                ["suffocate"] = Safe(() => c.CanSuffocate()),  // run 19: deep water drowns (shallow only wets)
                ["things"] = new JArray((c.Things ?? new List<Thing>()).Select(t => Clean(t.Name))),
                // What a hover shows (run 07, G7): "Locked (Lv X)", and whether it's someone's property.
                ["thingInfo"] = new JArray((c.Things ?? new List<Thing>()).Select(t => new JObject
                {
                    ["name"] = Clean(t.Name),
                    ["lockLv"] = t.c_lockLv,
                    ["npcProperty"] = t.isNPCProperty,
                    ["trait"] = t.trait?.GetType().Name,
                    // 0.35.0 (run 31): a twinkled Small Medal is roaming but stays out of every act list
                    // (PointTarget.ShouldIgnore skips isHidden/isMasked/isRoofItem; the walk skips ignoreAutoPick)
                    ["uid"] = t.uid,
                    ["placeState"] = t.placeState.ToString(),
                    ["hidden"] = t.isHidden,
                    ["masked"] = t.isMasked,
                    ["roofItem"] = t.isRoofItem,
                    ["ignoreAutoPick"] = t.ignoreAutoPick,
                })),
            });
        }

        // 0.35.0 (run 31): pick up a loose thing underfoot by uid through Chara.Pick, the call the game's own
        // "Pick up" act (ActPlan actPickOne) makes. Only on my own cell, only roaming, never NPC property,
        // and only when CanPick allows it (room in the pack): for things the act list can't show (a
        // twinkled Small Medal keeps its hidden bit from the map editor's Hidden tag).
        static JObject PickUp(int uid)
        {
            var pc = EClass.pc;
            if (pc == null) return Err("not in game");
            var t = pc.pos.Things.FirstOrDefault(x => x.uid == uid);
            if (t == null) return Err("no such thing on my cell");
            if (t.placeState != PlaceState.roaming) return Err("not loose: " + t.placeState);
            if (t.isNPCProperty) return Err("someone's property");
            if (!pc.CanPick(t)) return Err("can't pick it (the pack is full?)");
            var got = pc.Pick(t);
            return Ok(new JObject { ["picked"] = Clean(got?.Name ?? t.Name) });
        }

        // An inventory slot's right-click menu, as InvOwner.ShowContextMenu builds it: needs the
        // inventory open and a fresh `buttons` listing; N is that listing's index.
        static List<InvOwner.Interaction> lastInv;
        static Thing lastInvCard;

        static JObject InvActs(int i)
        {
            if (i < 0 || i >= lastButtons.Count || !lastButtons[i]) return Err("button index stale: call buttons again");
            var g = lastButtons[i] as ButtonGrid;
            if (g == null || g.invOwner == null || g.card == null) return Err("not an inventory slot");
            if (!EClass.pc.HasNoGoal) return Err("busy: the player is doing something");
            var list = g.invOwner.ListInteractions(g, true);
            list.Sort((a, b) => a.priority - b.priority);
            lastInv = list.ToList();
            lastInvCard = g.card as Thing;
            return Ok(new JObject
            {
                ["item"] = Clean(g.card.Name),
                ["acts"] = new JArray(lastInv.Select((it, k) => new JObject { ["i"] = k, ["text"] = Clean(it.name.lang()) })),
            });
        }

        static JObject InvDo(int i, JObject cmd = null)
        {
            if (lastInv == null || i < 0 || i >= lastInv.Count) return Err("no such act: call invacts again");
            var it = lastInv[i];
            var did = Clean(it.name.lang());
            // 0.30.0: a second return or evacuation scroll during a countdown cancels it and spends both
            if (did.StartsWith("Read", StringComparison.OrdinalIgnoreCase) && IsReturnScroll(lastInvCard)
                && EClass.player?.returnInfo != null && !((bool?)cmd?["force"] ?? false))
                return Err("a return is pending (" + EClass.player.returnInfo.turns + " turns left): reading another scroll cancels both (force=1 to do it anyway)");
            lastInv = null;
            it.action();
            return Ok(new JObject { ["did"] = did });
        }

        // An open inventory window's header buttons (buttonShared = the share lock, buttonSort,
        // buttonQuickSort, buttonExtra). The header shows them only while the mouse hovers the
        // window, so `buttons` never sees them. Name empty: list them. Otherwise press one, but
        // only if the game enabled it for this window (activeSelf) and it is interactable.
        // The container window a settings op acts on: an installed box's window (a layer of its
        // own), else the one carried bag open in the pack's floating windows (LayerInventory.listInv
        // holds those too; ui.layers doesn't). Run 14: naming the second backpack.
        static LayerInventory ContainerLayer(out string why, string bag = null)
        {
            why = null;
            var layer = EClass.ui.layers.OfType<LayerInventory>().LastOrDefault();
            if (layer && layer.invs.Count > 0) return layer;
            var carried = LayerInventory.listInv.Where(l => l && l.invs.Count > 0 && l.Inv.Container != null && !l.Inv.Container.IsPC).ToList();
            if (!string.IsNullOrEmpty(bag))
                carried = carried.Where(l => Clean(l.Inv.Container.Name).ToLowerInvariant().Contains(bag.ToLowerInvariant())).ToList();
            if (carried.Count == 1) return carried[0];
            why = carried.Count == 0 ? "no inventory window open" + (string.IsNullOrEmpty(bag) ? "" : " for " + bag)
                : "several carried bags are open (" + string.Join(", ", carried.Select(l => Clean(l.Inv.Container.Name))) + "): give bag=NAME or close all but one";
            return null;
        }

        static readonly string[] WinButtonNames = { "buttonShared", "buttonSort", "buttonQuickSort", "buttonExtra" };

        static JObject WinButton(string name)
        {
            var layer = ContainerLayer(out var why);
            if (!layer) return Err(why);
            var window = layer.invs[0].window;
            if (string.IsNullOrEmpty(name))
            {
                var arr = new JArray();
                foreach (var n in WinButtonNames)
                {
                    var b = Traverse.Create(window).Field(n).GetValue<UIButton>();
                    if (!b) continue;
                    var tip = b.tooltip != null ? (b.tooltip.text.IsEmpty() ? b.tooltip.lang : b.tooltip.text) : null;
                    arr.Add(new JObject { ["name"] = n, ["enabled"] = b.gameObject.activeSelf && b.interactable, ["tip"] = tip.IsEmpty() ? null : Clean(tip.lang()) });
                }
                return Ok(new JObject { ["window"] = Clean(layer.Inv.Container.Name), ["buttons"] = arr });
            }
            if (Array.IndexOf(WinButtonNames, name) < 0) return Err("name must be one of " + string.Join(", ", WinButtonNames));
            var btn = Traverse.Create(window).Field(name).GetValue<UIButton>();
            if (!btn || !btn.gameObject.activeSelf || !btn.interactable) return Err(name + " is not enabled for this window");
            btn.onClick.Invoke();
            return Ok(new JObject { ["pressed"] = name });
        }

        // The open container's distribution settings, the ones its window's Config > Distribution
        // menu sets (UIInventory: the priority slider -5..20, one toggle per ContainerFlag, "no
        // rotten"). That submenu is a hover popper the bridge can't open, so this sets the same
        // fields. They decide where shared items land: Delegated Farming's crops and residents'
        // put-aways go to the shared box with the highest priority that lets the category in
        // (Zone.FindSharedContainer; a set flag bit blocks that category). Run 12.
        // name: the same menu's "Change name" (Dialog.InputName sets c_altName; offered for any
        // container that isn't a character or a special container). Run 14: two carried
        // backpacks, and the tools find bags by name.
        static JObject BoxCfg(int? priority, string allow, bool? noRotten, string name = null, string bag = null)
        {
            var layer = ContainerLayer(out var why, bag);
            if (!layer) return Err(why);
            var con = layer.Inv.Container;
            if (con == null || con.IsPC || con.isChara) return Err("not a container window");
            if (name != null)
            {
                if (con.trait.IsSpecialContainer) return Err("the game offers no Change name for this container");
                con.c_altName = name;
            }
            var data = con.c_windowSaveData ?? layer.invs[0].window.saveData;
            if (data == null) return Err("this window has no settings");
            if (priority.HasValue) data.priority = Mathf.Clamp(priority.Value, -5, 20);
            if (!string.IsNullOrEmpty(allow))
            {
                var want = allow.ToLowerInvariant().Split(',').Select(s => s.Trim()).ToList();
                var blocked = ContainerFlag.none;
                foreach (ContainerFlag f in Enum.GetValues(typeof(ContainerFlag)))
                    if (f != ContainerFlag.none && !want.Contains("all") && !want.Contains(f.ToString()))
                        blocked |= f;
                data.flag = blocked;
            }
            if (noRotten.HasValue) data.noRotten = noRotten.Value;
            var allowed = new JArray();
            foreach (ContainerFlag f in Enum.GetValues(typeof(ContainerFlag)))
                if (f != ContainerFlag.none && !data.flag.HasFlag(f)) allowed.Add(f.ToString());
            return Ok(new JObject
            {
                ["box"] = Clean(con.Name),
                ["shared"] = con is Thing t && t.IsSharedContainer,
                ["priority"] = data.priority,
                ["allowed"] = allowed,
                ["noRotten"] = data.noRotten,
                ["onlyRottable"] = data.onlyRottable,
                ["advDistribution"] = data.advDistribution,
            });
        }

        // Load a LOCAL save from the title screen, as LayerLoadGame's Load button does. Never a
        // cloud save: the user's own characters live there (some share local world ids), and
        // the title list follows the user's config.cloud, which the bridge leaves alone.
        static JObject Load(string id)
        {
            if (string.IsNullOrEmpty(id) || id.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || id.Contains(".."))
                return Err("bad save id");
            bool inGame = false;
            try { inGame = EClass.core.game != null && EClass.pc != null; } catch { }
            if (inGame) return Err("a game is already loaded: quit to the title first");
            if (!Directory.Exists(CorePath.RootSave + id)) return Err("no local save " + id);
            foreach (var l in EClass.ui.layers.ToList())
                if (l is LayerLoadGame) l.Close();
            LayerTitle.KillActor();
            bool ok = Game.TryLoad(id, false, () => Game.Load(id, false));
            return ok ? Ok(new JObject { ["loading"] = id, ["cloud"] = false }) : Err("game says the save is incompatible");
        }

        static readonly System.Text.RegularExpressions.Regex Tags = new System.Text.RegularExpressions.Regex("<[^>]+>");
        static string Clean(string s) => s == null ? null : Tags.Replace(s, "").Trim();

        static JObject State()
        {
            var o = new JObject { ["frame"] = Time.frameCount };
            o["layers"] = Safe(Layers);
            o["drama"] = Safe(Drama);
            bool inGame = false;
            try { inGame = EClass.core != null && EClass.core.game != null && EClass.pc != null && EClass._map != null; } catch { }
            o["inGame"] = inGame;
            if (!inGame) return o;
            var pc = EClass.pc;
            o["pc"] = Safe(() => new JObject
            {
                ["name"] = pc.NameSimple,
                ["lv"] = pc.LV,
                ["exp"] = pc.exp,
                ["expNext"] = pc.ExpToNext,
                ["hp"] = pc.hp,
                ["maxHp"] = pc.MaxHP,
                ["mp"] = pc.mana.value,
                ["maxMp"] = pc.mana.max,
                ["sp"] = pc.stamina.value,
                ["maxSp"] = pc.stamina.max,
                ["hunger"] = pc.hunger.value,
                ["held"] = pc.held != null ? Clean(pc.held.Name) : null,
                ["hungerText"] = Safe(() => Clean(pc.hunger.GetText())),
                ["staminaText"] = Safe(() => Clean(pc.stamina.GetText())),
                ["ai"] = pc.ai != null ? pc.ai.GetType().Name + ":" + pc.ai.status : null,
                ["actCount"] = AM_Adv.actCount,
                ["gold"] = pc.GetCurrency("money"),
                ["goldBars"] = pc.GetCurrency("money2"),
                ["karma"] = EClass.player.karma,  // the character sheet's Karma (run 07, G8)
                ["date"] = Safe(() => { var d = EClass.world.date; return $"{d.year}-{d.month:00}-{d.day:00} {d.hour:00}:{d.min:00}"; }),
                ["x"] = pc.pos.x,
                ["z"] = pc.pos.z,
                ["turn"] = pc.turn,
                ["conditions"] = new JArray(pc.conditions.Select(c => c.GetType().Name)),
                ["pathWater"] = PathWater(pc),  // run 19: a walk heading into deep water (tools cancel it)
                // 0.30.0 (the review of 2026-10-23): what the loops used to scrape from the HUD or miss
                ["inWater"] = Safe(() => pc.Cell != null && pc.Cell.CanSuffocate()),
                ["breathesWater"] = BreathesWater(pc),
                ["riding"] = pc.ride != null ? Clean(pc.ride.Name) : null,  // 0.31.6
                ["burden"] = Safe(() => pc.burden.value), ["burdenMax"] = Safe(() => pc.burden.max),
                ["burdenPhase"] = Safe(() => pc.burden.GetPhase()), ["burdenText"] = Safe(() => Clean(pc.burden.GetText())),
                ["hungerPhase"] = Safe(() => pc.hunger.GetPhase()), ["spPhase"] = Safe(() => pc.stamina.GetPhase()),
                ["sleep"] = Safe(() => pc.sleepiness.value), ["sleepPhase"] = Safe(() => pc.sleepiness.GetPhase()),
                ["sleepText"] = Safe(() => Clean(pc.sleepiness.GetText())),
                ["return"] = Safe(ReturnInfo),  // the return/evacuation countdown, or null
                ["stacks"] = Safe(() => pc.things.Count(t => !t.isEquipped)),  // the pack's loose stacks (worn gear excluded: common.pack_full)
                ["conditionPhases"] = Safe(() => new JObject(pc.conditions.Select(c => new JProperty(c.GetType().Name, c.GetPhase())))),
            });
            o["transit"] = Safe(() => !pc.IsInActiveZone);  // between a zone move and its activation: the map below is stale
            o["zone"] = Safe(() =>
            {
                var z = EClass._zone;
                return new JObject
                {
                    ["name"] = z.NameWithLevel,
                    ["full"] = z.ZoneFullName,
                    ["danger"] = z.DangerLv,
                    ["town"] = z.IsTown,
                    ["nefia"] = z.IsNefia,
                    ["region"] = z.IsRegion,  // 0.30.0: the world map (fight.py matched the name before)
                    ["underwater"] = Safe(() => z.IsUnderwater),
                    // run 23: claiming Vernis made it the home zone, and a scroll of return then listed
                    // no Meadow (SpatialManager.ListReturnLocations: the home zone, never the zone I'm in)
                    ["pcFaction"] = Safe(() => z.IsPCFaction),
                    ["home"] = Safe(() => EClass.pc.homeZone?.Name),
                    ["isHome"] = Safe(() => EClass.pc.homeZone == z),
                    ["bounds"] = $"{EClass._map.bounds.x},{EClass._map.bounds.z},{EClass._map.bounds.maxX},{EClass._map.bounds.maxZ}",
                };
            });
            o["nearby"] = Safe(() =>
            {
                var arr = new JArray();
                foreach (var c in EClass._map.charas)
                {
                    if (c == pc || c.isDead) continue;
                    int dx = c.pos.x - pc.pos.x, dz = c.pos.z - pc.pos.z;
                    int dist = Math.Max(Math.Abs(dx), Math.Abs(dz));
                    if (dist > 12 || !pc.CanSee(c)) continue;
                    arr.Add(new JObject
                    {
                        ["name"] = c.NameSimple,
                        ["id"] = c.id,
                        ["uid"] = c.uid,
                        ["lv"] = c.LV,
                        ["dx"] = dx,
                        ["dz"] = dz,
                        ["dist"] = dist,
                        ["hostile"] = c.IsHostile(),
                        // Enemy < Neutral < Friend < Ally: a kick costs karma only at Friend+ (Card.Kick, run 07)
                        ["hostility"] = c.hostility.ToString(),
                        ["party"] = c.IsPCParty,
                        ["hpPct"] = c.MaxHP > 0 ? c.hp * 100 / c.MaxHP : 0,
                    });
                }
                return arr;
            });
            // 0.30.0: the hostiles in view with no radius cap, the party (a dead member drops out of
            // pc.party and stays on the map as a corpse: run 18's pet died unnoticed), the dead allies
            o["threat"] = Safe(() =>
            {
                int n = 0, bd = int.MaxValue;
                Chara best = null;
                foreach (var c in EClass._map.charas)
                {
                    if (c == pc || c.isDead || !c.IsHostile() || !pc.CanSee(c)) continue;
                    n++;
                    int d = Math.Max(Math.Abs(c.pos.x - pc.pos.x), Math.Abs(c.pos.z - pc.pos.z));
                    if (d < bd) { bd = d; best = c; }
                }
                return new JObject
                {
                    ["hostiles"] = n,
                    ["nearest"] = best == null ? null : new JObject { ["name"] = best.NameSimple, ["lv"] = best.LV, ["dist"] = bd, ["hpPct"] = best.MaxHP > 0 ? best.hp * 100 / best.MaxHP : 0 },
                };
            });
            o["party"] = Safe(() => new JArray(pc.party.members.Where(m => m != null && m != pc).Select(m =>
            {
                bool here = m.IsAliveInCurrentZone;
                var j = new JObject { ["name"] = m.NameSimple, ["uid"] = m.uid, ["lv"] = m.LV, ["hp"] = m.hp, ["maxHp"] = m.MaxHP, ["here"] = here };
                j["dist"] = here ? new JValue(Math.Max(Math.Abs(m.pos.x - pc.pos.x), Math.Abs(m.pos.z - pc.pos.z))) : JValue.CreateNull();
                return j;
            })));
            o["allyDead"] = Safe(() => new JArray(EClass._map.charas.Where(c => c.isDead && c.c_wasInPcParty).Select(c => c.NameSimple)));
            o["here"] = Safe(() => new JArray((pc.pos.cell.Things ?? new List<Thing>()).Select(t => ThingInfo(t, 0, 0))));
            o["things"] = Safe(() => NearbyThings(6, 25));
            o["log"] = Safe(() =>
            {
                var list = EClass.game.log.GetList(false);
                return new JArray(list.Skip(Math.Max(0, list.Count - 15)).Select(d => Clean(d.text)));
            });
            return o;
        }

        static JToken Layers()
        {
            var ui = EClass.ui;
            if (ui == null) return null;
            var arr = new JArray(ui.layers.Where(l => l).Select(l => l.GetType().Name + (string.IsNullOrEmpty(l.idLayer) ? "" : ":" + l.idLayer)));
            var top = ui.TopLayer;
            return new JObject
            {
                ["top"] = top ? top.GetType().Name : null, ["open"] = arr,
                // 0.30.0: the game's own "paused by a window" flag, and a context menu (not a layer)
                ["pause"] = Safe(() => ui.IsPauseGame),
                ["menu"] = Safe(() => ui.contextMenu != null && ui.contextMenu.isActive),
            };
        }

        static List<DramaChoice> Choices()
        {
            if (!LayerDrama.Instance || !LayerDrama.IsActive()) return null;
            var dm = LayerDrama.Instance.drama;
            var all = dm == null ? null : Traverse.Create(dm).Field("_choices").GetValue<List<DramaChoice>>();
            // _choices keeps entries from earlier steps (run 02 saw a stale `I came for ""`);
            // only a choice with a live button is on screen.
            return all?.Where(c => c.button && c.button.gameObject.activeInHierarchy).ToList();
        }

        static JToken Drama()
        {
            if (!LayerDrama.Instance || !LayerDrama.IsActive()) return null;
            var dm = LayerDrama.Instance.drama;
            var texts = dm && dm.dialog ? VisibleTexts(dm.dialog.gameObject) : new List<string>();
            var choices = Choices() ?? new List<DramaChoice>();
            return new JObject
            {
                ["text"] = new JArray(texts),
                ["choices"] = new JArray(choices.Select((c, i) => new JObject { ["i"] = i, ["text"] = c.text })),
            };
        }

        static Layer TopLayer()
        {
            try { return EClass.ui ? EClass.ui.TopLayer : null; } catch { return null; }
        }

        // text=, name=, card= (run 12 review): case-insensitive substring filters on the listing;
        // the indices stay those of the full listing, so `click N` works on a filtered result.
        static JObject Buttons(bool all, string text = null, string name = null, string card = null)
        {
            var top = TopLayer();
            IEnumerable<Button> src = !all && top ? top.GetComponentsInChildren<Button>(false) : UnityEngine.Object.FindObjectsOfType<Button>();
            lastButtons = src.Where(b => b && b.isActiveAndEnabled && b.interactable).ToList();
            var arr = new JArray();
            for (int i = 0; i < lastButtons.Count; i++)
            {
                var b = lastButtons[i];
                var o = new JObject { ["i"] = i, ["name"] = b.gameObject.name, ["text"] = Trunc(string.Join(" | ", VisibleTexts(b.gameObject)), 80) };
                if (name != null && (b.gameObject.name ?? "").IndexOf(name, StringComparison.OrdinalIgnoreCase) < 0) continue;
                if (text != null && ((string)o["text"] ?? "").IndexOf(text, StringComparison.OrdinalIgnoreCase) < 0) continue;
                if (b is ButtonGrid g && g.card != null)
                {
                    o["card"] = Clean(g.card.Name);
                    // My pack vs an open container or shop: both grids share a UI path.
                    o["mine"] = g.card.GetRootCard() == EClass.pc;
                    // which container the slot shows: the pack and a bag carried in it share UI
                    // paths, so tools tell them apart by this (run 04, bag.py)
                    if (g.card.parent is Card pc0) o["in"] = Clean(pc0 == EClass.pc ? "pack" : pc0.Name);
                }
                if (b is ButtonGrid gr && gr.recipe != null)
                {
                    o["card"] = Clean(gr.recipe.Name);
                    // Crafting a recipe for the first time pays old tickets (Recipe.TryGetFirstTimeBonus).
                    try { o["firstTime"] = gr.recipe.HasFirstTimeBonus(); } catch { }
                }
                if (b is ButtonGrid gi && gi.ing != null) o["ing"] = Clean(gi.ing.GetName()) + " x" + gi.ing.req;
                if (b is ButtonAbility ab && ab.source != null) o["card"] = Clean(ab.source.GetName());
                // F-key hotbar slots (WidgetHotbarEx*) carry a HotItem: name its type, e.g.
                // HotItemActionSleep is "Use bed in inventory" (run 05: their tooltips read empty)
                if (b is ButtonHotItem bh && bh.item is HotItem hti) o["hot"] = hti.GetType().Name;
                if (b is UIButton rb && rb.onRightClick != null) o["rclick"] = true;
                if (b is UIButton cb && cb.imageCheck && cb.imageCheck.gameObject.activeSelf) o["checked"] = true;
                // Icon buttons (a container's share lock, window tabs) say what they do only in a tooltip.
                // (The share lock sets tooltip.lang without enable, so enable isn't required.)
                if (b is UIButton ub && ub.tooltip != null)
                {
                    var tip = !string.IsNullOrEmpty(ub.tooltip.text) ? ub.tooltip.text : ub.tooltip.lang;
                    if (!string.IsNullOrEmpty(tip)) o["tip"] = Trunc(Clean(tip.lang()), 60);
                }
                if (all) o["path"] = ParentPath(b.transform, 3);
                if (card != null && ((string)o["card"] ?? "").IndexOf(card, StringComparison.OrdinalIgnoreCase) < 0) continue;
                arr.Add(o);
            }
            return new JObject { ["scope"] = !all && top ? top.GetType().Name : "all", ["buttons"] = arr };
        }

        // Stop the player's running task (training, fishing, walking) the way a player's click or
        // Wait key does: AM_Adv cancels only when the task allows a manual cancel.
        static JObject CancelTask()
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            if (pc.HasNoGoal) return Ok(new JObject { ["cancelled"] = false, ["ai"] = "idle" });
            if (!pc.ai.CanManualCancel()) return Err("this task can't be cancelled by hand: " + pc.ai.GetType().Name);
            var name = pc.ai.GetType().Name;
            pc.ai.Cancel();
            return Ok(new JObject { ["cancelled"] = true, ["was"] = name });
        }

        // Fight through the game's own auto-combat (run 16): GoalAutoCombat is what a click on a
        // hostile starts. Its safety net (Card.DamageHP): a lethal hit on the PC or a party member who
        // was not critically wounded when it began leaves them at 0 HP instead, aborts the combat and
        // costs 20% SP; further lethal hits that turn are evaded too (player.invlunerable). A single
        // Attack act has no such net. The AI runs until the foes are dead or it is aborted.
        static JObject AutoCombat(int uid, string tactics)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var at = EClass.game.config.autoCombat;
            // the PC's tactics in auto-combat are the Strategy tab's dropdown (Tactics.cs: at.idType;
            // the default "archer" keeps 3 cells off): `tactics` sets it as that dropdown does
            if (!string.IsNullOrEmpty(tactics))
            {
                if (!EClass.sources.tactics.map.ContainsKey(tactics)) return Err("no such tactics: " + tactics);
                at.idType = tactics;
            }
            if (EClass._zone.IsRegion) return Err("no auto-combat on the world map");
            Chara t = null;
            foreach (var c in EClass._map.charas) if (c.uid == uid) { t = c; break; }
            if (t == null || t.isDead) return Err("no such creature on this map: " + uid);
            if (!pc.CanSee(t)) return Err("can't see " + t.Name);
            pc.SetAI(new GoalAutoCombat(t));
            return Ok(new JObject { ["target"] = t.Name, ["startHP"] = EClass.player.autoCombatStartHP, ["ai"] = pc.ai.GetType().Name,
                ["tactics"] = at.idType, ["abortOnHalfHP"] = at.abortOnHalfHP, ["abortOnEnemyDead"] = at.abortOnEnemyDead,
                ["useHotbar"] = at.bUseHotBar, ["useInventory"] = at.bUseInventory, ["dontChase"] = at.bDontChase });
        }

        // run 24 (the user: "can you ride and do other things?"): riding trains Riding every few turns
        // (Chara tick: ModExp(226, 40 + affinity stage) on a local map, 5 on the world map), but my speed
        // becomes the mount's, cut by its weight against my Riding (Chara.RefreshSpeed): home work only.
        // The game's own ActRide.Ride / Unride, with ActRide.Perform's checks.
        static JObject Ride(int? uid, bool off)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            if (off)
            {
                if (pc.ride == null) return Err("not riding");
                var was = pc.ride.Name;
                ActRide.Unride(pc);
                return Ok(new JObject { ["unride"] = Clean(was), ["speed"] = pc.Speed });
            }
            if (EClass._zone.IsRegion) return Err("mount on a local map, not the world map");
            Chara t = null;
            foreach (var c in EClass._map.charas) if (c.uid == uid) { t = c; break; }
            if (t == null || t.isDead) return Err("no such creature on this map: " + uid);
            if (pc.pos.Distance(t.pos) > 1) return Err(t.Name + " is not beside me");
            if (t.host != null || t.IsMultisize || !t.IsPCFaction || !t.trait.CanJoinParty || t.memberType != FactionMemberType.Default)
                return Err("can't ride " + t.Name + " (ActRide's rules: my faction, a party member, one cell)");
            ActRide.Ride(pc, t);
            return Ok(new JObject { ["riding"] = Clean(t.Name), ["speed"] = pc.Speed, ["ridability"] = t.Ridability.ToString() });
        }

        // Close the top UI layer as its own close button does (never via Cancel, which can open
        // the System menu when only a container window is open).
        static JObject CloseTop()
        {
            var top = TopLayer();
            if (top == null) return Ok(new JObject { ["closed"] = null });
            var name = top.GetType().Name;
            top.Close();
            return Ok(new JObject { ["closed"] = name });
        }

        static JObject Texts(bool all, int max)
        {
            var top = TopLayer();
            var go = !all && top ? top.gameObject : null;
            var texts = go ? VisibleTexts(go) : UnityEngine.Object.FindObjectsOfType<Text>().Where(t => t.isActiveAndEnabled && !string.IsNullOrWhiteSpace(t.text)).Select(t => t.text.Trim()).ToList();
            return new JObject { ["scope"] = go ? top.GetType().Name : "all", ["texts"] = new JArray(texts.Select(t => Trunc(t, max))) };
        }

        static string ParentPath(Transform t, int depth)
        {
            var names = new List<string>();
            for (var p = t.parent; p && names.Count < depth; p = p.parent) names.Add(p.name);
            names.Reverse();
            return string.Join("/", names);
        }

        static List<string> VisibleTexts(GameObject go) =>
            go.GetComponentsInChildren<Text>(false).Where(t => t.isActiveAndEnabled && !string.IsNullOrWhiteSpace(t.text)).Select(t => t.text.Trim()).ToList();

        // expect= (0.25.0, run 15): the text the caller saw on button i. Any `buttons` call, from
        // any tool, replaces the saved listing; run 14's look.py did so between a Policy-tab
        // listing and its clicks, and `click 16` pressed button 16 of the whole screen (Tax Free
        // Land went off). With expect, a click on a button whose text or card no longer contains
        // it is refused before anything is pressed.
        static JObject Expect(JObject cmd)
        {
            var want = (string)cmd["expect"];
            if (string.IsNullOrEmpty(want)) return null;
            int i = (int)cmd["i"];
            if (i < 0 || i >= lastButtons.Count || !lastButtons[i]) return Err("button index stale: call buttons again");
            var b = lastButtons[i];
            var seen = string.Join(" | ", VisibleTexts(b.gameObject));
            if (b is ButtonGrid g && g.card != null) seen += " | " + Clean(g.card.Name);
            if (seen.IndexOf(want, StringComparison.OrdinalIgnoreCase) >= 0) return null;
            return Err($"button {i} is now '{Trunc(seen, 80)}', not '{want}': the listing changed; call buttons again");
        }

        static JObject Click(int i)
        {
            if (i < 0 || i >= lastButtons.Count || !lastButtons[i] || !lastButtons[i].isActiveAndEnabled)
                return Err("button index stale: call buttons again");
            var b = lastButtons[i];
            // An F-key hotbar slot: UIButton.Press waits for a real pointer, so nothing happened
            // (run 05, the F5 sleep). Run the slot's own action as its onClick listener does.
            // The name is read before the press (run 12): a press can destroy its own button (a
            // shop restock, a return scroll's destination list), and reading it after threw a
            // NullReferenceException for a click that had taken effect.
            var name = b.gameObject.name;
            if (b is ButtonHotItem hb && hb.item is HotItem hi && hb.widget != null)
            {
                if (EClass.ui.BlockInput) return Err("the UI is blocking input");
                UIButton.buttonPos = hb.transform.position;
                var hot = hi.GetType().Name;
                hi.OnClick(hb, hb.widget.hotbar);
                return Ok(new JObject { ["clicked"] = name, ["hot"] = hot });
            }
            try { PointerClick(b.gameObject); }
            catch (Exception e) { return Err(Describe(e) + " inside the press of " + name + " (it may have taken effect: read the state before retrying)"); }
            return Ok(new JObject { ["clicked"] = name });
        }

        // A right click on a UI button runs its onRightClick, as UIButton's deferred click does
        // for the right mouse button (abilities: use; hotbar slots and others: their own action).
        static JObject RightClick(int i)
        {
            if (i < 0 || i >= lastButtons.Count || !lastButtons[i] || !lastButtons[i].isActiveAndEnabled)
                return Err("button index stale: call buttons again");
            var ub = lastButtons[i] as UIButton;
            if (ub == null || ub.onRightClick == null) return Err("this button has no right-click action");
            var name = ub.gameObject.name;
            try { ub.onRightClick(); }
            catch (Exception e) { return Err(Describe(e) + " inside the right-click of " + name + " (it may have taken effect)"); }
            return Ok(new JObject { ["rclicked"] = name });
        }

        // Shift+click on an inventory slot: the game's own quick move (InvOwner.OnShiftClick) into
        // the top other inventory window, e.g. a container opened from the pack (run 04: the
        // Cooler Box opens as a window the drag-only UI fills; the user wanted the food in it).
        // CanShiftClick gates on the Shift key, so its other checks are repeated here through
        // the same InvOwner, minus the key: an item the game won't let you hold, or no
        // destination window, is refused.
        static JObject ShiftClick(int i)
        {
            if (i < 0 || i >= lastButtons.Count || !lastButtons[i] || !lastButtons[i].isActiveAndEnabled)
                return Err("button index stale: call buttons again");
            var bg = lastButtons[i] as ButtonGrid;
            if (bg == null || bg.invOwner == null || bg.card == null) return Err("not an inventory slot with an item");
            var t = bg.card.Thing;
            if (t == null) return Err("not a thing");
            if (!bg.invOwner.AllowHold(t)) return Err("the game won't let you move this item");
            var before = t.parent;
            bg.invOwner.OnShiftClick(bg, false);
            return Ok(new JObject { ["moved"] = Clean(t.Name), ["changed"] = t.parent != before });
        }

        // Drag an inventory slot onto another slot (a hotbar/toolbelt slot, a container slot, an
        // empty pack slot): the drop the UI makes when a drag ends on a ButtonGrid, i.e.
        // from.invOwner.OnDrag(from, to, execute: true) with DragItemCard.DragInfo for both ends,
        // so the game's own checks (AllowHold, stacking, full, equip rules) all apply. Run 04: the
        // toolbelt's hotbar slots are storage outside the pack grid (the user's tip).
        static JObject Drag(int i, int j, int n = 0)
        {
            bool Bad(int k) => k < 0 || k >= lastButtons.Count || !lastButtons[k] || !lastButtons[k].isActiveAndEnabled;
            if (Bad(i) || Bad(j)) return Err("button index stale: call buttons again");
            var a = lastButtons[i] as ButtonGrid;
            var b = lastButtons[j] as ButtonGrid;
            if (a == null || a.invOwner == null || a.card == null) return Err("source is not an inventory slot with an item");
            if (b == null || b.invOwner == null) return Err("target is not an inventory slot");
            var t = a.card.Thing;
            var before = t.parent;
            var from = new DragItemCard.DragInfo(a);
            var to = new DragItemCard.DragInfo(b);
            // Not OnDrag itself: its first branch drops the thing on the ground whenever the real
            // mouse isn't over the UI (run 04: the Putit landed at my feet), and it opens the
            // hotbar register layer. This is its targeted-drop branch for inventory targets.
            if (to.invOwner == null || !b.interactable) return Err("target slot doesn't accept drops");
            if (!to.invOwner.AllowTransfer) return Err("target doesn't allow transfers");
            // 0.30.0: a drag onto a stack of the same thing merged badly once (run 13: three hide
            // textures vanished); the move goes through a container instead. merge=1 overrides.
            if (b.card != null && b.card != a.card && Clean(b.card.Name) == Clean(a.card.Name) && !((bool?)current?.cmd["merge"] ?? false))
                return Err("the target holds a stack of the same item: never merge by drag (run 13 lost three textures); move both into one container, or pass merge=1");
            // n: how many of the stack to move (run 04: one skin of two into the butcher's tool)
            var tr = new InvOwner.Transaction(from, to, n > 0 ? Math.Min(n, t.Num) : t.Num);
            if (!tr.IsValid()) return Err("the game says this move isn't valid: " + Clean(tr.GetTextDetail() ?? ""));
            // Run 14: a drag from a shop's stock onto a pack slot took 6 rations unpaid. The UI buys
            // on the click (Process(startTransaction: true) charges, then the drop lands as a free
            // trade); a drop with a pack slot as `to` counts as FreeTrade (InvOwner.Transaction).
            // Buying goes through the shop item's right-click menu: invacts N, then "Buy".
            if (InvOwner.HasTrader && tr.currency != CurrencyType.None && !tr.sell && tr.FreeTrade)
                return Err("this drag would take a shop item without paying: buy it with `invacts N` then invdo \"Buy\"");
            bool ok = tr.Process();
            return Ok(new JObject { ["dragged"] = Clean(t.Name), ["accepted"] = ok, ["changed"] = t.parent != before,
                                    ["now_in"] = t.parent is Card c0 ? Clean(c0 == EClass.pc ? "pack" : c0.Name) : null });
        }

        // Placement height: what the place helper's height button does (click +1, right-click -1,
        // Shift+wheel): ActionMode.Build.ModAltitude, read back from ActionMode.Build.altitude. A
        // wall torch placed at +0 sits on the floor in front of the wall (the user, run 04: mount
        // it higher). d = 0 only reads it.
        static JObject Altitude(int d)
        {
            if (d != 0) ActionMode.Build.ModAltitude(d);
            return Ok(new JObject { ["altitude"] = ActionMode.Build.altitude });
        }

        // Hover: show a button's tooltip the way the mouse does (UIButton.ShowTooltip minus its
        // real-mouse checks). The tooltip builds over a frame; read it with `tip`.
        static JObject Hover(int i)
        {
            if (i < 0 || i >= lastButtons.Count || !lastButtons[i] || !lastButtons[i].isActiveAndEnabled)
                return Err("button index stale: call buttons again");
            var ub = lastButtons[i] as UIButton;
            if (ub == null || ub.tooltip == null) return Err("this button has no tooltip");
            TooltipManager.Instance.ShowTooltip(ub.tooltip, ub.transform);
            // The manager hides it again next frame (the real mouse isn't on the button), but
            // SetData has already written the note: read it now.
            return Ok(new JObject { ["hovered"] = ub.gameObject.name, ["texts"] = new JArray(TooltipTexts().Select(t => Trunc(Clean(t), 400))) });
        }

        static List<string> TooltipTexts() =>
            UnityEngine.Object.FindObjectsOfType<UITooltip>().Where(t => t && t.isActiveAndEnabled)
                .SelectMany(t => VisibleTexts(t.gameObject)).ToList();

        static JObject Choose(int i)
        {
            var choices = Choices();
            if (choices == null) return Err("no dialog choices open");
            if (i < 0 || i >= choices.Count) return Err($"choice {i} out of range 0..{choices.Count - 1}");
            var c = choices[i];
            if (c.button) PointerClick(c.button.gameObject);
            else if (c.onClick != null) c.onClick();
            else return Err("choice has no button or action");
            return Ok(new JObject { ["chose"] = c.text });
        }

        // The open context menu (UIContextMenuManager.currentMenu): a menu is not a layer, so
        // `buttons` under a layer never listed it and the first review left it open. No argument
        // lists its entries; i= or text= presses one through the same path as `click`; close=1
        // hides it (Hide returns early unless the manager's autoClose is set: set it for the call).
        static JObject Menu(int? i, string text, bool close)
        {
            var mgr = EClass.ui?.contextMenu;
            var m = mgr?.currentMenu;
            if (m == null || m.isDestroyed) return Err("no context menu open");
            string Label(Button b) => Clean(string.Join(" ", b.GetComponentsInChildren<Text>(false)
                .Where(t => t.isActiveAndEnabled && !string.IsNullOrWhiteSpace(t.text)).Select(t => t.text.Trim())));
            var buttons = m.GetComponentsInChildren<Button>(false).Where(b => b && b.isActiveAndEnabled && b.interactable).ToList();
            if (close)
            {
                bool auto = mgr.autoClose;
                mgr.autoClose = true;
                try { m.Hide(); } finally { mgr.autoClose = auto; }
                return Ok(new JObject { ["closed"] = true, ["open"] = mgr.isActive });
            }
            if (i == null && string.IsNullOrEmpty(text))
                return Ok(new JObject
                {
                    ["system"] = m.system,
                    ["entries"] = new JArray(buttons.Select((b, k) => new JObject { ["i"] = k, ["text"] = Label(b) })),
                });
            Button target;
            if (i != null)
            {
                if (i < 0 || i >= buttons.Count) return Err("no entry " + i + " (the menu has " + buttons.Count + ")");
                target = buttons[i.Value];
            }
            else
            {
                var hits = buttons.Where(b => Label(b).StartsWith(text, StringComparison.OrdinalIgnoreCase)).ToList();
                if (hits.Count != 1) return Err(hits.Count == 0 ? "no entry starts with '" + text + "'" : "several entries start with '" + text + "': give more of the text");
                target = hits[0];
            }
            var label = Label(target);
            PointerClick(target.gameObject);
            return Ok(new JObject { ["pressed"] = label, ["open"] = Safe(() => mgr.isActive) });
        }

        // UIButton defers a pointer click through BaseCore.WaitForEndOfFrame and drops it while
        // EInput.skipFrame > 0; from the bridge that did nothing (2026-10-15, window minimized).
        // So a UIButton is pressed through its own _OnPress, which keeps the game's checks
        // (locked, active, interactable), sound and onClick. Other buttons get a pointer click.
        static readonly MethodInfo UIButtonPress = AccessTools.Method(typeof(UIButton), "_OnPress");

        static void PointerClick(GameObject go)
        {
            var ub = go.GetComponent<UIButton>();
            if (ub && UIButtonPress != null) { UIButtonPress.Invoke(ub, null); return; }
            var ev = new PointerEventData(EventSystem.current) { button = PointerEventData.InputButton.Left };
            ExecuteEvents.Execute(go, ev, ExecuteEvents.pointerClickHandler);
        }

        // ---- deferred ops (run 12 review: they replace the tools' sleep-and-poll loops) ----

        static string Describe(Exception e)
        {
            while (e is TargetInvocationException tie && tie.InnerException != null) e = tie.InnerException;
            return e.GetType().Name + ": " + e.Message;
        }

        static string BlockingTop()
        {
            var top = TopLayer();
            if (top == null) return null;
            var name = top.GetType().Name;
            return name == "LayerInventory" ? null : name;
        }

        static readonly HashSet<string> GuardedOps = new HashSet<string>
            { "goto", "walkto", "move", "step", "do", "invdo", "invacts", "drag", "shiftclick", "autocombat", "act", "pick" };
        // 0.30.1 (run 21): the trash can, the butcher's tool, pickers, the millstone, the ration
        // maker and the tax chest take items through their own drag grid; 0.30.0 refused every
        // drag into them ("window open: LayerDragGrid") and trash.py reported 30 dumps of nothing.
        static readonly HashSet<string> InventoryOps = new HashSet<string> { "invdo", "invacts", "drag", "shiftclick" };
        // input actions that answer or close what is open, or change nothing in the world
        static readonly HashSet<string> FreeActions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            { "Cancel", "CancelUI", "Confirm", "MenuInventory", "MenuChara", "MenuJournal", "MenuAbility", "Log", "Report", "QuickSave", "Help", "Pause", "Examine", "ShowGrid" };

        // Why the world must not be acted on now, or null: a window other than a container's
        // (the game ignores world input under it), an open context menu, a running drama. The
        // reads, the UI ops that close or answer things, and the AI cancel are never guarded.
        static string Busy(JObject cmd, string op)
        {
            if (!GuardedOps.Contains(op)) return null;
            if ((bool?)cmd["force"] ?? false) return null;
            if (op == "act" && FreeActions.Contains((string)cmd["action"] ?? "")) return null;
            var blocking = BlockingTop();
            if (blocking == "LayerDragGrid" && InventoryOps.Contains(op)) blocking = null;
            if (blocking != null) return "window open: " + blocking;
            try { if (EClass.ui != null && EClass.ui.contextMenu != null && EClass.ui.contextMenu.isActive) return "context menu open: click an entry or closetop first"; } catch { }
            try { if (LayerDrama.IsActive()) return "drama open: talk.py first"; } catch { }
            return null;
        }

        // The return or evacuation countdown (Player.returnInfo; null when none is pending). A second
        // scroll read while it runs cancels it, "The air relaxes", and both scrolls are spent
        // (runs 05, 10, 20): InvDo refuses the read, and state reports the turns left.
        static JToken ReturnInfo()
        {
            var ri = EClass.player?.returnInfo;
            if (ri == null) return null;
            string dest = null;
            try { if (ri.uidDest != 0) dest = EClass.game.spatials.Find(ri.uidDest)?.Name; } catch { }
            return new JObject { ["turns"] = ri.turns, ["evac"] = ri.isEvac, ["askDest"] = ri.askDest, ["dest"] = dest };
        }

        static bool IsReturnScroll(Thing t)
        {
            if (t == null) return false;
            try
            {
                var row = (t.trait as TraitScroll)?.GetRefElement();
                if (row != null && (row.id == 8220 || row.id == 8221)) return true;
            }
            catch { }
            var n = Clean(t.Name).ToLowerInvariant();
            return n.Contains("scroll") && (n.Contains("of return") || n.Contains("of evacuation"));
        }

        static bool BreathesWater(Chara p)
        {
            try { return p.HasElement(429) || p.HasElement(1252); } catch { return false; }
        }

        static void Defer(JObject cmd, Func<JObject> pending, Func<JObject> onTimeout)
        {
            if (current == null) throw new InvalidOperationException("no request to defer");
            current.pending = pending;
            current.onTimeout = onTimeout;
            current.deadline = Environment.TickCount + Math.Min(Math.Max((int?)cmd["timeout"] ?? 15000, 1000), 180000);
        }

        static JObject Snapshot(string why)
        {
            var pc = EClass.pc;
            var top = TopLayer();
            return new JObject
            {
                ["why"] = why,
                ["done"] = why == "done" || why == "arrived",
                ["x"] = pc?.pos.x, ["z"] = pc?.pos.z,
                ["hp"] = pc?.hp, ["maxHp"] = pc?.MaxHP,
                ["zone"] = Safe(() => EClass._zone.ZoneFullName),
                ["top"] = top ? top.GetType().Name : null,
                ["ai"] = pc?.ai != null ? pc.ai.GetType().Name : null,
            };
        }

        // The reply comes when the condition holds, or at the timeout (ok, done=false, why=timeout).
        // until: idle (no AI task), zone (the zone changed from `zone` or from the one at the call),
        // layer (the top layer is no longer `layer`, or the one at the call), moved (position
        // changed), frames (n frames passed).
        static JObject WaitFor(JObject cmd)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            string until = (string)cmd["until"] ?? "idle";
            int n = (int?)cmd["n"] ?? 1;
            string zone0 = (string)cmd["zone"] ?? EClass._zone.ZoneFullName;
            string layer0 = (string)cmd["layer"] ?? TopLayer()?.GetType().Name;
            int x0 = pc.pos.x, z0 = pc.pos.z, frame0 = Time.frameCount;
            Func<bool> holds;
            switch (until)
            {
                case "idle": holds = () => EClass.pc.HasNoGoal; break;
                case "zone": holds = () => EClass.pc != null && EClass._map != null && EClass.pc.IsInActiveZone && !EClass.game.isLoading && EClass._zone.ZoneFullName != zone0; break;
                case "layer": holds = () => TopLayer()?.GetType().Name != layer0; break;
                case "moved": holds = () => EClass.pc.pos.x != x0 || EClass.pc.pos.z != z0; break;
                case "frames": holds = () => Time.frameCount - frame0 >= n; break;
                default: return Err("until must be idle, zone, layer, moved or frames");
            }
            Defer(cmd, () => holds() ? Ok(Snapshot("done")) : null, () => Ok(Snapshot("timeout")));
            return null;
        }

        // goto plus a deferred reply: when the player arrives, stops short, a hostile comes within
        // `r` cells (the walk is cancelled; weakOk ignores foes 3+ levels below), HP drops under `hp`
        // percent, a window opens, or the zone changes (stairs, a world-map ambush). A stairway as
        // the target is refused unless stairs=true (goto took stairs by accident, lessons.md).
        static JObject WalkTo(int x, int z, JObject cmd)
        {
            var pc = EClass.pc;
            if (pc == null) throw new InvalidOperationException("not in game");
            var c = CellAt(x, z);
            if (c == null) return Err("target is off the map");
            if (!c.isSeen) return Err("target cell is unexplored");
            if (!((bool?)cmd["stairs"] ?? false) && c.HasStairs) return Err("the target is a stairway: pass stairs=true to take it");
            if (c.CanSuffocate() && !BreathesWater(pc))
                return Err(Safe(() => EClass._zone.IsUnderwater).ToString() == "True"
                    ? "an underwater zone: every cell suffocates without water breathing (the tools' --breathe gate)"
                    : "the target is deep water (suffocation): never walk there (run 19)");
            // 0.30.0: Squashed cancels AI_Goto in the game itself (Player.TooHeavyToMove): say so
            int burdenPhase = 0;
            try { burdenPhase = pc.burden.GetPhase(); } catch { }
            if (burdenPhase >= 4) return Err("Squashed (burden phase 4): the game refuses to move; drop or store weight first");
            int r = (int?)cmd["r"] ?? 4;
            int hpPct = (int?)cmd["hp"] ?? 60;
            bool weakOk = (bool?)cmd["weakOk"] ?? false;
            string zone0 = EClass._zone.ZoneFullName;
            if (pc.pos.x == x && pc.pos.z == z) return Ok(Snapshot("arrived"));
            var wet = WaterOnWay(pc, x, z);  // 0.30.0: before the first step, not a frame after it
            if (wet != null) { var ws0 = Snapshot("water"); ws0["water"] = wet; return Ok(ws0); }
            pc.SetAIImmediate(new AI_Goto(new Point(x, z), 0));
            current.onAbandon = () => StopWalk(EClass.pc);
            Defer(cmd, () =>
            {
                var p = EClass.pc;
                if (p == null || EClass._map == null) return null;
                if (!p.IsInActiveZone || EClass.game.isLoading) return null;  // a zone switch in progress
                if (EClass._zone.ZoneFullName != zone0) return Ok(Snapshot("zone"));
                if (p.pos.x == x && p.pos.z == z) return Ok(Snapshot("arrived"));
                var blocking = BlockingTop();
                if (blocking != null) { StopWalk(p); return Ok(Snapshot("window")); }
                if (p.hp * 100 < hpPct * p.MaxHP) { StopWalk(p); return Ok(Snapshot("hp")); }
                // run 19: stop before the path enters deep water (the drowning in Port Kapul)
                var water = PathWater(p);
                if (water != null) { StopWalk(p); var ws = Snapshot("water"); ws["water"] = water; return Ok(ws); }
                var foe = NearestHostile(p, r, weakOk);
                if (foe != null)
                {
                    StopWalk(p);
                    var snap = Snapshot("hostile");
                    snap["hostile"] = foe.NameSimple; snap["hostileLv"] = foe.LV;
                    snap["hostileDist"] = Math.Max(Math.Abs(foe.pos.x - p.pos.x), Math.Abs(foe.pos.z - p.pos.z));
                    return Ok(snap);
                }
                if (p.HasNoGoal) return Ok(Snapshot("stopped"));
                return null;
            }, () => { StopWalk(EClass.pc); return Ok(Snapshot("timeout")); });
            return null;
        }

        static void StopWalk(Chara p)
        {
            try { if (p != null && !p.HasNoGoal && p.ai.CanManualCancel()) p.ai.Cancel(); } catch { }
        }

        static Chara NearestHostile(Chara p, int r, bool weakOk)
        {
            Chara best = null;
            int bestDist = int.MaxValue;
            foreach (var c in EClass._map.charas)
            {
                if (c == p || c.isDead || !c.IsHostile() || !p.CanSee(c)) continue;
                if (weakOk && c.LV <= p.LV - 3) continue;
                int d = Math.Max(Math.Abs(c.pos.x - p.pos.x), Math.Abs(c.pos.z - p.pos.z));
                if (d <= r && d < bestDist) { bestDist = d; best = c; }
            }
            return best;
        }

        // ---- helpers ----

        static JToken Safe(Func<JToken> f)
        {
            try { return f(); }
            catch (Exception e) { return "ERR " + e.GetType().Name + ": " + e.Message; }
        }

        static string Trunc(string s, int n) => s == null || s.Length <= n ? s : s.Substring(0, n) + "…";
        static JObject Ok(JToken data) => new JObject { ["ok"] = true, ["data"] = data };
        static JObject Err(string msg) => new JObject { ["ok"] = false, ["error"] = msg };
    }
}
