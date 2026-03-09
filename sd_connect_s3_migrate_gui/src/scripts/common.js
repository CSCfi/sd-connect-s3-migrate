// Convenience functions used across the application

export function timeout(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getReadableSize(val) {
  const BYTE_UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];

  let size = val ?? 0;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < BYTE_UNITS.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  const decimalSize = size.toFixed(1);
  let result = decimalSize.toString();

  return `${result} ${BYTE_UNITS[unitIndex]}`;
}

export function getReadableTime(seconds) {
  const minSec = 60;
  const hourSec = 60 * minSec;
  const daySec = 24 * hourSec;
  const monthSec = 30 * daySec;

  if (seconds < minSec) return "less than 1 minute";
  if (seconds >= monthSec) return "more than a month";

  let time = "";
  let spans = [
    { unit: "day", sec: daySec },
    { unit: "hour", sec: hourSec },
    { unit: "minute", sec: minSec },
  ];
  let secondsLeft = seconds;

  spans.forEach((span, i) => {
    // ceiling-round last unit not to be too optimistic
    const val = i === spans.length - 1 ? Math.ceil(secondsLeft / span.sec) : Math.floor(secondsLeft / span.sec);
    if (val) {
      time = time.concat(`${val} ${span.unit}${val > 1 ? "s" : ""} `);
      secondsLeft -= span.sec * val;
    }
  });

  return time;
}
