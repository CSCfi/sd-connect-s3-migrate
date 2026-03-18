// Convenience functions used across the application

/**
 * Estimated bandwidth of 100Mbps
 */
export const estimatedBytesPerSec = (100 * 1000000) / 8;

/**
 * Set a timeout for a number of milliseconds
 * @param {number} ms - milliseconds
 */
export function timeout(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Get a human readable size of a bucket (copied over from SD Connect codebase)
 * @param {number} val - the size to parse
 */
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

/**
 * Get a human readable time in format x days x hours x minutes
 * @param {number} seconds - seconds to parse
 */
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

/**
 * Get c-status parameters from recommended migration action number
 * @param {number} statusNum - recommended action number
 */
export function getBucketStatus(statusNum) {
  if (statusNum >= 5) {
    return { type: "error", value: "Urgent" };
  }
  // For now cases when migration not needed is not considered
  return null;
}
