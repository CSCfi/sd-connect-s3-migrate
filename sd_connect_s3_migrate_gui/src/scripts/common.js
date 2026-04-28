// Convenience functions used across the application

/**
 * Estimated bandwidth of 100Mbps
 */
export const estimatedBytesPerSec = (50 * 1000000) / 8;

export const migrationStages = {
  starting: "starting",
  sharing: "sharing",
  headers: "headers",
  objects: "objects",
};

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
 * Get a human readable time estimate as "approximately x hours/days"
 * @param {number} seconds - seconds to parse
 */
export function getTimeEstimate(seconds) {
  const minSec = 60;
  const hourSec = 60 * minSec;
  const daySec = 24 * hourSec;

  if (seconds < minSec) return "couple of minutes";

  if (seconds > hourSec * 18) {
    let val = Math.ceil((seconds - hourSec * 6) / daySec);
    return "approximately " + val + " day" + (val > 1 ? "s" : "");
  }
  let val = Math.ceil(seconds / hourSec);
  return "approximately " + val + " hour" + (val > 1 ? "s" : "");
}

/**
 * Get c-status parameters from recommended migration action number
 * @param {number} statusNum - recommended action number
 */
export function getBucketStatus(statusNum) {
  if (statusNum === 2) {
    return { type: "error", value: "Urgent" };
  }
  if (statusNum === 1) {
    return { type: "warning", value: "By the end of 2026" };
  }
  return null;
}
