const { paintTrajectory, buildTrajectoryMeta } = require('../../utils/trajectory.js');
const { getWindowMetrics, rpxToPx } = require('../../utils/responsive.js');

Component({
  properties: {
    result: {
      type: Object,
      value: null,
      observer: 'onResultChange',
    },
    heightRpx: {
      type: Number,
      value: 380,
    },
  },

  data: {
    metaText: '',
    hasData: false,
    canvasWidthPx: 300,
    canvasHeightPx: 200,
  },

  lifetimes: {
    attached() {
      this._updateCanvasBox();
    },
    ready() {
      this._updateCanvasBox();
      if (this._pendingResult) {
        this._paintWithResult(this._pendingResult);
      }
    },
  },

  methods: {
    _updateCanvasBox() {
      const m = getWindowMetrics();
      // 页面左右各 24rpx padding + card 内边距约 24rpx → 可用宽度
      const padPx = rpxToPx(48 + 48);
      const widthPx = Math.max(200, Math.floor(m.windowWidth - padPx));
      const heightPx = Math.max(160, Math.floor(rpxToPx(this.properties.heightRpx || 380)));
      this.setData({
        canvasWidthPx: widthPx,
        canvasHeightPx: heightPx,
      });
      return { widthPx, heightPx, dpr: m.pixelRatio };
    },

    onResultChange(result) {
      const hasData = Boolean(
        result &&
          Array.isArray(result.trajectory) &&
          result.trajectory.length > 0 &&
          result.deck_profile &&
          Array.isArray(result.deck_profile.points) &&
          result.deck_profile.points.length > 0
      );
      this._pendingResult = hasData ? result : null;
      this.setData({ hasData, metaText: hasData ? this.data.metaText : '' }, () => {
        if (hasData) {
          // 给布局一帧时间，再按固定 CSS 像素尺寸取 node 绘制
          setTimeout(() => this._paintWithResult(result), 32);
        }
      });
    },

    _paintWithResult(result) {
      if (!result || !result.trajectory || !result.deck_profile) return;
      const box = this._updateCanvasBox();
      const cssW = box.widthPx;
      const cssH = box.heightPx;
      const dpr = box.dpr || 2;

      // 必须等 style 宽高落到节点后再取 canvas node
      this.setData(
        {
          canvasWidthPx: cssW,
          canvasHeightPx: cssH,
        },
        () => {
          setTimeout(() => this._drawNode(result, cssW, cssH, dpr, 0), 16);
        }
      );
    },

    _drawNode(result, cssW, cssH, dpr, attempt) {
      wx.createSelectorQuery()
        .in(this)
        .select('#trajCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          const info = res && res[0];
          const canvas = info && info.node;
          if (!canvas) {
            if (attempt < 20) {
              setTimeout(() => this._drawNode(result, cssW, cssH, dpr, attempt + 1), 50);
            } else {
              console.error('[trajectory-chart] 无法获取 canvas node');
              this.setData({ metaText: '轨迹画布初始化失败，请重试仿真' });
            }
            return;
          }

          const ctx = canvas.getContext('2d');
          if (!ctx) {
            this.setData({ metaText: '当前基础库不支持 Canvas 2D' });
            return;
          }

          canvas.width = Math.round(cssW * dpr);
          canvas.height = Math.round(cssH * dpr);
          ctx.setTransform(1, 0, 0, 1, 0, 0);
          ctx.scale(dpr, dpr);

          try {
            const meta = paintTrajectory(ctx, result, cssW, cssH);
            this.setData({ metaText: buildTrajectoryMeta(meta) });
            this._pendingResult = null;
          } catch (e) {
            console.error('[trajectory-chart] 绘制失败', e);
            this.setData({ metaText: `轨迹绘制失败: ${e.message || e}` });
          }
        });
    },
  },
});
