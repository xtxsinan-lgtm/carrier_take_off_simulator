const { paintTrajectory, buildTrajectoryMeta } = require('../../utils/trajectory.js');
const { rpxToPx } = require('../../utils/responsive.js');

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
    ready: false,
  },

  lifetimes: {
    attached() {
      this._canvasReady = false;
    },
  },

  methods: {
    onResultChange(result) {
      if (result && result.trajectory && result.trajectory.length && result.deck_profile) {
        this.setData({ ready: true }, () => this.draw());
      } else {
        this.setData({ ready: false, metaText: '' });
      }
    },

    draw() {
      const result = this.properties.result;
      if (!result || !result.trajectory || !result.deck_profile) return;

      const query = this.createSelectorQuery();
      query
        .select('#trajCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res || !res[0] || !res[0].node) return;
          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const cssW = res[0].width;
          const cssH = res[0].height;
          const dpr = wx.getSystemInfoSync().pixelRatio || 2;
          canvas.width = cssW * dpr;
          canvas.height = cssH * dpr;
          ctx.scale(dpr, dpr);

          const meta = paintTrajectory(ctx, result, cssW, cssH);
          this.setData({ metaText: buildTrajectoryMeta(meta) });
        });
    },
  },
});
