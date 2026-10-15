# Doodle animation plan

The doodle is the site's character. This plan covers the two places he performs: the preloader
(the first impression) and the hero on the home page (where visitors can play with him).

## Principles

Every motion follows the classic animation principles, adapted for a flat, outlined cartoon:

- **Weight and physics.** Heavy things start slowly, overshoot and settle. Feet never slide while
  they are on the ground. A body that stops keeps moving for a moment (momentum).
- **Anticipation.** Every big action is preceded by a small opposite one: a crouch before a jump,
  a pull back before a shove.
- **Follow-through and overlap.** Parts do not stop together: the head lags the torso, the hair lags
  the head, hands settle after the arms.
- **Squash and stretch.** Landings squash, launches stretch, always keeping volume.
- **Arcs.** Hands, feet and the head move along curves, never straight lines.
- **Timing.** Fast actions read as effort or surprise; holds give the eye time to read a pose.
  Everything runs at 30 sampled frames per second with eased interpolation in between.
- **Appeal and restraint.** One clear idea per beat. Nothing loops so long it gets annoying.

## The rig

A vector puppet built from the two reference drawings, so it stays sharp at any size:

| Part | Source | Joint |
| --- | --- | --- |
| Head (with glasses, eyes, hair) | traced from the drawing | neck, with lag |
| Torso (hoodie, tee, hood) | traced, filled in behind the arms | pelvis; breathes |
| Upper arm, forearm (sleeve, lime stripe, cuff) | drawn as vectors in the same style | shoulder, elbow |
| Hands | traced from the drawing | wrist |
| Thigh, shin, shoe | drawn as vectors | hip, knee, ankle (heel-to-toe roll) |

Limbs are solved with two-bone IK: hands and feet are placed where they should be (on the logo, on
the ground) and the elbows and knees bend on their own. Round joints and a one-shape outline keep
every pose seamless.

Two views exist: the **pushing pose** (three-quarter, facing left) and the **front view** (standing,
smiling). A cartoon "turn" (a squash to a sliver and a pop into the other view) switches between them.

## 1. Preloader film (about 4 s)

| Time | Beat | What happens |
| --- | --- | --- |
| 0.0 to 0.2 s | Empty stage | Paper and grid; the counter starts. |
| 0.2 to 2.2 s | The push | He walks in from the right pushing the m/ logo. The logo is heavy: it moves in stick-slip surges. On each step his body drives forward first (elbows compress), then the logo breaks free (arms extend). Feet are planted, heels lift on push-off, the swinging foot arcs and lands heel first. Head strains with a slight tremble; torso breathes; one bead of sweat flies off. Dust stays where it is kicked up. |
| 2.2 to 2.45 s | Anticipation | He sinks, elbows bend deep, head down. |
| 2.45 to 2.6 s | The big shove | He explodes forward; the logo slides to dead centre and thuds (squash, dust cloud). |
| 2.6 to 2.85 s | Momentum | He stumbles a step past his balance, catches himself, exhales (a little puff). |
| 2.85 to 3.0 s | The turn | He straightens, then spins to face the camera. |
| 3.0 to 3.55 s | Ta-da | Front view: dip, hop with stretch, squash on landing, settle. The curtain lifts mid-hop and the hero shows the same character rising, so the story continues. |

Delivery: one self-contained animated SVG per cut (wide/tall × light/dark), only the matching one
downloads, and it runs before any JavaScript. Reduced motion shows the final pose.

## 2. Home page: the doodle you can play with

The hero shows his upper half. He already follows the cursor, blinks and breathes. Clicking him
plays a short "move" (0.6 to 1.4 s), each built on the same principles, then he returns to idle.

| Move | Idea |
| --- | --- |
| Wave | Arm swings up in an arc, hand waves three times with overlapping wrist motion, settles. |
| Jump | Dip, stretch up out of frame a little, squash on landing, hair and head lag. |
| Spin | Squash, quick turn through a sliver, pop back with a wobble. |
| Shrug | Shoulders up, head tilts, eyebrows (pupils) up, drop with a small bounce. |
| Nod | Two quick nods with the head leading and the body following. |
| Startled | (rapid clicks) jumps back with stretched pose and pupils shrinking, then recovers. |
| Look | Turns and points his gaze at the Work section; a click then scrolls there. |

How it behaves:

- Each click plays the next move, never the same one twice in a row; a speech bubble line can pair
  with it.
- A double-click or five quick clicks play the rare "startled" move.
- Cursor tracking pauses during a move and eases back in after it.
- Moves are keyframed poses played by a tiny engine on requestAnimationFrame (no library), loaded
  only on the first click so the page stays fast.
- Reduced motion: no moves, only the speech bubble.

## 3. Later

- Doodle reacts to scrolling (glances at the navbar logo as it docks).
- Footer cameo: he sits on the MR.DEVELOPER4U wordmark.
- 404 page: he looks for the missing page with a torch.

## Quality checks for every animation

1. Frame strips at 60 ms intervals for each beat: no gaps at joints, no sliding feet, arcs are smooth.
2. Light and dark, wide and tall.
3. Mobile Lighthouse stays at or above 85 for performance and 100 for accessibility.
4. Reduced motion respected.
