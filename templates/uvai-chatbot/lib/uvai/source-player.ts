export function sourcePlayback(videoId: string, seconds: number) {
  if (!/^[A-Za-z0-9_-]{11}$/.test(videoId) || !Number.isFinite(seconds) || seconds < 0 || seconds > 86400) {
    throw new Error("invalid_source_timestamp");
  }
  const start = Math.floor(seconds);
  return {
    embed: `https://www.youtube-nocookie.com/embed/${videoId}?start=${start}`,
    external: `https://www.youtube.com/watch?v=${videoId}&t=${start}s`,
    label: `${Math.floor(start / 60)}:${String(start % 60).padStart(2, "0")}`,
  };
}
