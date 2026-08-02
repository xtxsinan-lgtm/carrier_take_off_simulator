Component({
  properties: {
    /** [{id, label}, ...] */
    modeList: {
      type: Array,
      value: [],
    },
    current: {
      type: String,
      value: 'ski_jump',
    },
  },

  methods: {
    onTap(e) {
      const mode = e.currentTarget.dataset.mode;
      if (mode && mode !== this.data.current) {
        this.triggerEvent('change', { mode });
      }
    },
  },
});
