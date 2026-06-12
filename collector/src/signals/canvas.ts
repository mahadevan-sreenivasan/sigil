export async function collectCanvasHash(): Promise<string> {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  if (!ctx) return '';

  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(0, 0, 256, 128);
  ctx.fillStyle = '#333333';
  ctx.font = '18px Arial';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText('Sigil canvas fp', 10, 60);
  ctx.beginPath();
  ctx.arc(200, 64, 30, 0, Math.PI * 2);
  ctx.fillStyle = '#6699cc';
  ctx.fill();
  ctx.closePath();

  const dataUrl = canvas.toDataURL('image/png');
  const msgBuffer = new TextEncoder().encode(dataUrl);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
