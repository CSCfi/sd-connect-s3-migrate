// Convenience functions used across the application

export function timeout(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
