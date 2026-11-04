# Small Medals

Text drawn from Ylvapedia (https://ylvapedia.wiki, its contributors) is CC BY-SA 4.0; this file adapts it.

Where the hidden Small Medals are, for planning trips (the user, 2026-10-29: "you need to carry a shovel and dig
for medals... so you are looking for those in game next time"). Source: ylvapedia Elin:Small_Medal, read
2026-10-29, summarized; the wiki has the exact landmarks. Miral and Garokk's Workshop trades them (fact #854).

**How they work** (the game's code and the wiki): a static map's medals lie hidden at fixed spots, as installed
things. Stepping on the cell says *twinkle* (TraitCurrencyMedal.OnStepped) and turns the medal loose; then pick
it up. `tools/medals.py` lists the ones on a wiki map's explored cells and `--take` walks onto each reachable
one; `look.py` prints a MEDALS line on those maps. The tool refuses other maps: the bridge sees hidden things the
player can't, so it is used only where the spots are public.

**Other sources:** nefia boss and floor chests (about one a three conquests in run 30), Poppy's treasure-map
chests (1-8 each), fishing, Silver Bells, pickpocketing town chests, the fortune drum's third tier (fact #395).

**The hard ones** (a deliberate step, never by the tool): under furniture (a hammer, or a rod of teleport moves
the furniture; hammering town property is a crime), behind a wall or a bridge (a shovel: digging in a town is a
crime too, sneakmine.py's rules), in deep water (walkto refuses: teleport, or water breathing).

| Map | Medals | Notes |
|---|---:|---|
| Port Kapul | 8 | Fighters Guild prison and graveyard, the basement (from the south bank), inn pool, lighthouse, the den, the harbor bridge (dig it, or swim from the pub), the ship |
| Quiet Beach | 2 | the west sand and the sea by a floating bowl |
| The Cursed Manor | 2 | under a willow; one in the pond |
| Derphy | 10 | four in the Thieves Guild (one under the casino table), stable, brothel, a house, the gallows, the lion's cage, outside the west wall |
| Tinker's Camp | 3 | the hill's corner tree, the ranch's water trough, by a tent |
| Little Garden | 2 | behind the model's pedestal, the park's corner |
| Olvina | 4 | brewery, flower garden, picnic area, the hot springs |
| Old Keep | 4 | kitchen, gargoyle room, rose garden, the path's end outside |
| Orphanage | 2 | the farm; under the teacher's desk (furniture) |
| Mysilia | 9 | NW corner, the palace garden (cut a tree), behind the arboreum, under a palace bed, the atrium's bushes, the river by the SE wall, two houses, the crypt |
| Merchant Guild | 3 | by a cart (destroy it), between shelves, the courtyard trees |
| Willow | 3 | the hill, the mansion's corner, Cetrus's room |
| Hill Cave | 1 | between the straw piles |
| Vernis | 1 | the central hill's SE side, by a skull |
| Aquli Teola | 4 | the mayor's room, under a mini table (furniture), the server area, by a light stand |
| Yowyn | 8 | the tilled terraces, a house, a pond (water), the ranch, the graves, the wheat field, the informer's room, B1 by the cat |
| Palmia | 7 | by a palace bed, the palace pond (water), the training room, the fountain, an alley, the security bureau, the vault (dig into the SW wall) |
| Fortune Bell | 9 | three on 1F (one among mines), six on 2F |
| The Embassy | 2 | the entrance pond (water), behind the building |
| Truce Ground | 3 | the generator, the altar of Luck, the waterway |
| Specwing | 5 | across three floors; one needs a teleport or a broken floor |
| Doga Ruins Camp | 3 | the stable, a well, the pasture |
| Nefu Village | 4 | the bamboo, a mansion screen, the lake (water), the cliff seats |
| The Graveyard | 2 | the north, the hut's bed |
| Lumiest | 11 | the Mages Guild B1 (three), several underwater (teleport), boats, an inn bed, a west island |
| Mifu Village | 5 | the labor machine, the river, the Altar of Trickery's cliff, the rice paths, behind a house |
| Where Winds Rest | 1 | by the large fossil tree |
| Village of Atonement | 4 | the watch fire, an abandoned house, the swing, the moongate |
| Miral and Garokk's Workshop | 3 | the two NE bedroom beds, the SW storehouse by the sawmill |
| Noyel | 5 | the paddock, the church, the frozen pond, the waystone, the bar |
| The Mansion of Younger Sister | 3 | the fir trees, a bedroom, the laboratory |
| Seeker's Keep | 5 | castle-wall recesses and the frozen sea |
| Garden of Eternity | 3 | the pond (water), the cherry tree, the mahjong room |
| **33 maps** | **141** | none listed for Lumiest Crater, Permafrost, the Arena |

**Run 31 first:** Miral's Workshop's three (the cure visit), then the towns on the way of each trip.
