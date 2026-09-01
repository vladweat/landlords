import { useEffect, useState } from 'react';

export function useCountUp(end: number, duration = 800) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (end <= 0) { setValue(end); return; }
    let start = 0;
    const step = end / (duration / 16);
    const decimals = Number.isInteger(end) ? 0 : 2;
    const factor = 10 ** decimals;
    const timer = setInterval(() => {
      start += step;
      if (start >= end) { setValue(end); clearInterval(timer); }
      else { setValue(Math.round(start * factor) / factor); }
    }, 16);
    return () => clearInterval(timer);
  }, [end, duration]);

  return value;
}
