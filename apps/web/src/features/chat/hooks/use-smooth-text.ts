import { useEffect, useRef, useState } from "react";

// Presentation only: the query cache always retains the complete server text.
export function useSmoothText(
  text: string,
  streaming: boolean,
  revealEpoch = 0,
) {
  const [visible, setVisible] = useState(() => (streaming ? "" : text));
  const shown = useRef(visible);
  const previousEpoch = useRef(revealEpoch);
  useEffect(() => {
    const skip = previousEpoch.current !== revealEpoch;
    previousEpoch.current = revealEpoch;
    if (skip || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      shown.current = text;
      setVisible(text);
      return;
    }
    if (!text.startsWith(shown.current)) {
      shown.current = "";
      setVisible("");
    }
    let frame = 0;
    let last = performance.now();
    let budget = 0;
    const tick = (now: number) => {
      const remaining = text.length - shown.current.length;
      // Smooth small chunks; catch up gradually when the transport delivers a burst.
      budget +=
        (Math.min(now - last, 50) * Math.min(500, 70 + remaining * 0.65)) /
        1000;
      last = now;
      const count = Math.min(remaining, Math.floor(budget));
      if (count > 0) {
        let end = shown.current.length + count;
        // Never split a UTF-16 surrogate pair.
        if (end < text.length && /[\uD800-\uDBFF]/.test(text[end - 1])) end++;
        shown.current = text.slice(0, end);
        budget -= count;
        setVisible(shown.current);
      }
      if (shown.current.length < text.length)
        frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [text, revealEpoch]);
  return visible;
}
