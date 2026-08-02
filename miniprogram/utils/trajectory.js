const { fmtNum } = require('./physics.js');

function xAxisStepM(maxX) {
  if (maxX <= 80) return 10;
  if (maxX <= 200) return 20;
  if (maxX <= 400) return 50;
  return 100;
}

function resolveTakeoffX(result, deckPts, traj) {
  const deckExit = traj.find((p) => p.phase === 'deck_exit');
  if (deckExit) return deckExit.x;
  if (result.deck_profile && result.deck_profile.takeoff_distance_m != null) {
    return result.deck_profile.takeoff_distance_m;
  }
  if (result.distance_m != null) return result.distance_m;
  return deckPts[deckPts.length - 1][0];
}

/**
 * 在 Canvas 2D 上下文上绘制起飞轨迹（逻辑尺寸 cssW × cssH，已 scale dpr）。
 */
function paintTrajectory(ctx, result, cssW, cssH) {
  const deckPts = result.deck_profile.points;
  const traj = result.trajectory;
  const takeoffX = resolveTakeoffX(result, deckPts, traj);
  const takeoffLabelM = result.distance_m ?? result.deck_profile?.takeoff_distance_m ?? takeoffX;
  const carrierDeckM = result.deck_profile.total_deck_length_m;

  const xs = [...deckPts.map((p) => p[0]), ...traj.map((p) => p.x), takeoffX];
  if (carrierDeckM) xs.push(carrierDeckM);
  const ys = [...deckPts.map((p) => p[1]), ...traj.map((p) => p.y)];
  const minX = 0;
  const maxX = Math.max(...xs, 1) * 1.08;
  const minY = Math.min(0, ...ys) - 2;
  const maxY = Math.max(...ys, result.deck_profile.lip_height_m || 0, 1) + 8;

  const pad = { l: 36, r: 12, t: 24, b: 36 };
  const plotW = cssW - pad.l - pad.r;
  const plotH = cssH - pad.t - pad.b;

  const toX = (x) => pad.l + ((x - minX) / (maxX - minX)) * plotW;
  const toY = (y) => pad.t + plotH - ((y - minY) / (maxY - minY)) * plotH;

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = '#1a2332';
  ctx.fillRect(0, 0, cssW, cssH);

  ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)';
  ctx.lineWidth = 1;
  const xStep = xAxisStepM(maxX);
  for (let gx = 0; gx <= maxX; gx += xStep) {
    ctx.beginPath();
    ctx.moveTo(toX(gx), pad.t);
    ctx.lineTo(toX(gx), pad.t + plotH);
    ctx.stroke();
  }
  for (let gy = Math.ceil(minY / 5) * 5; gy <= maxY; gy += 5) {
    ctx.beginPath();
    ctx.moveTo(pad.l, toY(gy));
    ctx.lineTo(pad.l + plotW, toY(gy));
    ctx.stroke();
  }

  ctx.fillStyle = '#94a3b8';
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let gx = 0; gx <= maxX; gx += xStep) {
    ctx.fillText(String(gx), toX(gx), pad.t + plotH + 4);
  }
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let gy = Math.ceil(minY / 5) * 5; gy <= maxY; gy += 5) {
    if (gy !== 0) ctx.fillText(String(gy), pad.l - 4, toY(gy));
  }

  ctx.strokeStyle = 'rgba(248, 113, 113, 0.6)';
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(toX(takeoffX), pad.t);
  ctx.lineTo(toX(takeoffX), pad.t + plotH);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = '#94a3b8';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  ctx.fillText(`滑跑 ${fmtNum(takeoffLabelM, 1)} m`, toX(takeoffX), pad.t - 4);

  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  deckPts.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(toX(x), toY(y));
    else ctx.lineTo(toX(x), toY(y));
  });
  ctx.stroke();

  ctx.fillStyle = 'rgba(100, 116, 139, 0.25)';
  ctx.beginPath();
  deckPts.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(toX(x), toY(y));
    else ctx.lineTo(toX(x), toY(y));
  });
  ctx.lineTo(toX(deckPts[deckPts.length - 1][0]), toY(minY));
  ctx.lineTo(toX(deckPts[0][0]), toY(minY));
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.beginPath();
  traj.forEach((p, i) => {
    if (i === 0) ctx.moveTo(toX(p.x), toY(p.y));
    else ctx.lineTo(toX(p.x), toY(p.y));
  });
  ctx.stroke();

  const first = traj[0];
  const deckExit = traj.find((p) => p.phase === 'deck_exit');
  const last = traj[traj.length - 1];
  const markers = [[first, '#4ade80'], ...(deckExit ? [[deckExit, '#fb923c']] : []), [last, '#fbbf24']];
  for (const [pt, color] of markers) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(toX(pt.x), toY(pt.y), 4, 0, Math.PI * 2);
    ctx.fill();
  }

  return {
    takeoffLabelM,
    maxHeightM: Math.max(...traj.map((p) => p.y)),
    pointCount: traj.length,
  };
}

function buildTrajectoryMeta(meta) {
  if (!meta) return '';
  return (
    `滑跑距离 ${fmtNum(meta.takeoffLabelM, 1)} m · ` +
    `${meta.pointCount} 个采样点 · ` +
    `最大高度 ${fmtNum(meta.maxHeightM, 1)} m`
  );
}

module.exports = {
  paintTrajectory,
  buildTrajectoryMeta,
  resolveTakeoffX,
};
