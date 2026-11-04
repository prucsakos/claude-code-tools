# Animation techniques

Techniques that work with the renderer's seek model (SKILL.md, "4. Build the scenes"): every CSS animation is paused and seeked to the frame time, and `window.renderAt(t, beats)` is called each frame. Anything driven by transitions, timers or `requestAnimationFrame` does not render. Every snippet below is used in the demo `examples/animations/`; preview it with:

```
python SKILL_DIR/make_video.py SKILL_DIR/examples/animations/storyboard.json --preview
```

## 1. Beat-timed reveal and stagger

When it helps: a list or a set of parts that the narration names one after another. Each part appears when it is named, so the viewer looks at the right place.

```html
<li class="in rise" style="--at: calc(var(--b0) + 0 * .15s)">Read the input</li>
<li class="in rise" style="--at: calc(var(--b0) + 1 * .15s)">Transform it</li>
<li class="in rise" style="--at: calc(var(--b0) + 2 * .15s)">Write the result</li>
```

Caveats: a stagger of .1–.2 s reads as one group; for parts that the narration names separately, use one beat per part instead. `rise` and `pop` move the element, so use them on block or inline-block elements.

## 2. SVG path drawing

When it helps: arrows, graphs, routes and outlines whose direction matters. Drawing shows where the line starts and where it goes.

```html
<path class="draw" pathLength="1" d="M 40 360 C 200 360 240 60 660 40"
      style="--at: var(--b1); --dur: 1.6s; stroke: var(--c1); stroke-width: 10; fill: none"/>
```

Caveats: the shape needs `pathLength="1"`, because `.draw` animates `stroke-dashoffset` from 1 to 0. It draws the stroke only; fade the fill in with a separate `in` element.

## 3. Motion along a path

When it helps: a packet through a network, a value through a pipeline, a planet in an orbit. The moving object shows the flow that a static arrow only implies.

```css
.packet {
  offset-path: path("M 0 300 C 200 0 500 0 700 300");
  offset-rotate: 0deg;
  animation: travel 2s var(--ease) var(--b0) both;
}
@keyframes travel { from { offset-distance: 0%; } to { offset-distance: 100%; } }
```

Caveats: `offset-path` coordinates are in CSS pixels of the element's containing block, not in the units of an SVG `viewBox`. Draw the visible track with the same path in an SVG of the same size and no scaling, or the object leaves the track. The path places the element's center; shift the track by half the element size to match. `offset-rotate: 0deg` keeps the object upright; `auto` turns it along the path.

## 4. Shape morphing

When it helps: one thing that becomes another (a square that becomes a circle, a bar chart that becomes a line chart), so the viewer sees that they are the same object.

```css
.blob { animation: morph 1.6s var(--ease) var(--b1) both; }
@keyframes morph {
  from { d: path("M 100 0 C 200 0 200 0 200 100 C 200 200 200 200 100 200 C 0 200 0 200 0 100 C 0 0 0 0 100 0 Z"); }
  to   { d: path("M 100 0 C 155 0 200 45 200 100 C 200 155 155 200 100 200 C 45 200 0 155 0 100 C 0 45 45 0 100 0 Z"); }
}
```

Caveats: the CSS `d` property animates in Chromium only, which is what the renderer uses. Both paths must have the same list of commands (here M, four C, Z); otherwise the shape jumps instead of morphing. For shapes with different structure, compute the points in `renderAt` and set the `d` attribute yourself.

## 5. Number counter

When it helps: a quantity that grows or shrinks (steps, cost, users). Counting up makes the size of the number felt.

```js
const ease = (x) => 1 - (1 - x) ** 3;
const clamp01 = (x) => Math.min(1, Math.max(0, x));
window.renderAt = (t, beats) => {
  const value = Math.round(1000 * ease(clamp01((t - beats[0]) / 2)));
  count.textContent = value.toLocaleString("en-US");
};
```

Caveats: compute the value from `t` only, never from the previous frame, because the renderer can seek to any time. Use a tabular font or a fixed width when the digits jump left and right.

## 6. Canvas or JavaScript simulation

When it helps: physics, particles, sorting steps or plots, where the motion follows a rule that CSS cannot express.

```js
window.renderAt = (t, beats) => {
  const swing = Math.max(0, t - beats[1]);
  const angle = 0.6 * Math.cos(2 * Math.PI * swing / 1.6) * Math.exp(-0.15 * swing);
  if (angle === drawnAngle) return false;
  drawnAngle = angle;
  ctx.clearRect(0, 0, 640, 480);
  // draw the rod and the bob at angle
};
```

Caveats: the frame must be a pure function of `t`. Step-by-step integration (`x += v * dt`) gives a different result when the renderer seeks, so use a closed-form solution, or re-run the integration from 0 to `t` with a fixed step each frame. For random particles, use a seeded generator recreated each frame. Return `false` when nothing changed, so that the renderer can reuse the previous screenshot. When one scene has several `renderAt` effects, compute them in the same function.

## 7. Camera pan and zoom

When it helps: a diagram that is too large to read at once. Show the whole diagram first, then move in on the part the narration explains, so the viewer keeps the context.

```css
.viewport { position: relative; flex: 1; min-height: 0; overflow: hidden; }
.camera { position: absolute; transform-origin: 0 0; animation: zoom-to-middle 1.6s var(--ease) var(--b1) both; }
@keyframes zoom-to-middle {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(-1040px, -180px) scale(2.2); }
}
```

Caveats: put the diagram in a wrapper with `overflow: hidden` and animate the wrapper's child only. With `transform-origin: 0 0`, a point (x, y) of the diagram ends at (x·s + tx, y·s + ty), which makes the target easy to compute. Scale an SVG, not a bitmap, so text stays sharp. Text that is 44 px at scale 1 is too large when zoomed in and too small when zoomed out; check both ends in the preview.

## 8. Focus by dimming the other parts

When it helps: the narration talks about one part of a full picture. Dimming the rest keeps the context visible but tells the viewer where to look.

```html
<g class="dim" style="--at: var(--b2)">
  <rect x="0" y="180" width="420" height="200"/>
  <text x="210" y="295">Parse</text>
</g>
```

Caveats: `dim` fades to 25% and stays there; to bring a part back, wrap it in another element with an `in` animation on a later beat, because an element takes one animation class. Dim groups of parts rather than every shape on its own.

## 9. Animation libraries: GSAP, anime.js, Lottie

When it helps: a motion is already easy to write in a library, or a designer delivers a Lottie file. Libraries play on the wall clock by default, which the renderer does not capture; each can be paused and seeked, so a small adapter in `renderAt` makes every frame exact. Build the timeline on the first `renderAt` call, because the beat times arrive in its `beats` argument. The demo `examples/libraries/` renders all three.

GSAP, a paused timeline:

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script>
  let tl = null, shownTime = null;
  window.renderAt = (t, beats) => {
    tl ??= gsap.timeline({ paused: true })
      .to(box, { x: 1200, duration: 1.2 }, beats[0])
      .to(box, { rotation: 180, duration: 1.2 }, beats[1]);
    const time = Math.min(t, tl.duration());
    if (time === shownTime) return false;
    shownTime = time;
    tl.seek(time);
  };
</script>
```

anime.js, `autoplay: false` and times in milliseconds:

```html
<script src="https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js"></script>
<script>
  let tl = null, shownMs = null;
  window.renderAt = (t, beats) => {
    tl ??= anime.timeline({ autoplay: false, duration: 1200 })
      .add({ targets: "#first", scaleY: [0.05, 0.5] }, beats[0] * 1000)
      .add({ targets: "#second", scaleY: [0.05, 1] }, beats[1] * 1000);
    const ms = Math.min(t * 1000, tl.duration);
    if (ms === shownMs) return false;
    shownMs = ms;
    tl.seek(ms);
  };
</script>
```

Lottie (lottie-web), inline `animationData` and `sceneReady` for the async load:

```html
<script src="https://cdn.jsdelivr.net/npm/lottie-web@5.12.2/build/player/lottie.min.js"></script>
<script>
  const animationData = { /* the Lottie JSON, pasted inline */ };
  const anim = lottie.loadAnimation({ container: player, renderer: "svg", loop: false, autoplay: false, animationData });
  window.sceneReady = new Promise((resolve) => anim.isLoaded ? resolve() : anim.addEventListener("DOMLoaded", resolve));
  let shownFrame = null;
  window.renderAt = (t, beats) => {
    const frame = Math.min(anim.totalFrames - 1, Math.max(0, (t - beats[0]) * 30));
    if (frame === shownFrame) return false;
    shownFrame = frame;
    anim.goToAndStop(frame, true);  // or goToAndStop(ms, false) for a time in milliseconds
  };
</script>
```

Caveats: never let a library play (`play()`, `autoplay: true`, GSAP tweens outside a paused timeline): wall-clock playback does not render and differs between runs. Keep the `renderAt` return value honest: return `false` only when the seek position is the same as in the previous call, and clamp the position to the timeline length so that static holds reuse the screenshot. Pin the CDN version; the scene needs the network when it renders, and a failed load prints a warning. `fetch()` of a local file fails from `file://`, so paste Lottie JSON inline. A Lottie frame equal to `op` is past the last layer frame and shows nothing; stop at `op - 1`.
