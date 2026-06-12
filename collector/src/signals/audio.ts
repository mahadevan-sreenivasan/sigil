async function sha256Hex(data: Float32Array): Promise<string> {
  const buffer = new Uint8Array(data.buffer);
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function collectAudioHash(): Promise<string | null> {
  try {
    if (typeof OfflineAudioContext === 'undefined') return null;

    const ctx = new OfflineAudioContext(1, 4500, 44100);

    const oscillator = ctx.createOscillator();
    oscillator.type = 'triangle';
    oscillator.frequency.value = 10000;

    const compressor = ctx.createDynamicsCompressor();
    compressor.threshold.value = -50;
    compressor.knee.value = 40;
    compressor.ratio.value = 12;
    compressor.attack.value = 0;
    compressor.release.value = 0.25;

    oscillator.connect(compressor);
    compressor.connect(ctx.destination);

    oscillator.start(0);

    const rendered = await ctx.startRendering();
    const channelData = rendered.getChannelData(0);

    return sha256Hex(channelData);
  } catch {
    return null;
  }
}
