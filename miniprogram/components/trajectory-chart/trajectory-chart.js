const { paintTrajectory, buildTrajectoryMeta } = require('../../utils/trajectory.js');

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
  },

  lifetimes: {
    ready() {
      // 组件布局完成后再尝试绘制，避免 type=2d canvas 宽高为 0
      if (this.properties.result) {
        this.scheduleDraw();
      }
    },
  },

  methods: {
    onResultChange(result) {
      const hasData = Boolean(
        result &&
          result.trajectory &&
          result.trajectory.length &&
          result.deck_profile &&
          result.deck_profile.points &&
          result.deck_profile.points.length
      );
      this.setData({ hasData, metaText: hasData ? this.data.metaText : '' }, () => {
        if (hasData) this.scheduleDraw();
      });
    },

    scheduleDraw() {
      this._drawAttempts = 0;
      // 双 nextTick：先等 setData 落 DOM，再等 scroll-view 完成布局
      wx.nextTick(() => {
        wx.nextTick(() => this.draw());
      });
    },

    draw() {
      const result = this.properties.result;
      if (
        !result ||
        !result.trajectory ||
        !result.trajectory.length ||
        !result.deck_profile ||
        !result.deck_profile.points
      ) {
        return;
      }

      this.createSelectorQuery()
        .select('#trajCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          const nodeInfo = res && res[0];
          const canvas = nodeInfo && nodeInfo.node;
          const cssW = nodeInfo ? nodeInfo.width : 0;
          const cssH = nodeInfo ? nodeInfo.height : 0;

          if (!canvas || cssW < 8 || cssH < 8) {
            this._drawAttempts = (this._drawAttempts || 0) + 1;
            if (this._drawAttempts <= 12) {
              setTimeout(() => this.draw(), 50);
            }
            return;
          }

          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio || 2;
          canvas.width = Math.round(cssW * dpr);
          canvas.height = Math.round(cssH * dpr);
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

          const meta = paintTrajectory(ctx, result, cssW, cssH);
          this.setData({ metaText: buildTrajectoryMeta(meta) });
        });
    },
  },
});
