/// <reference lib="webworker" />

let interval: ReturnType<typeof setInterval> | null = null;

addEventListener('message', ({ data }) => {
  if (data.type === 'start') {
    if (interval) clearInterval(interval);
    interval = setInterval(() => {
      postMessage({ type: 'tick' });
    }, data.ms ?? 30_000);
    postMessage({ type: 'tick' });
  }
  if (data.type === 'stop') {
    if (interval) clearInterval(interval);
  }
});