const { SCENE_MAP, buildReport } = require('../../utils/risk-data')

Page({
  data: {
    imagePath: '',
    analyzing: false,
    sceneOptions: Object.keys(SCENE_MAP).map((key) => ({
      key,
      label: SCENE_MAP[key].label
    })),
    selectedScene: 'bathroom',
    report: null
  },

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera', 'album'],
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]

        if (!file) {
          return
        }

        this.setData({
          imagePath: file.tempFilePath,
          report: null
        })
      }
    })
  },

  onSceneChange(e) {
    this.setData({
      selectedScene: e.detail.value
    })
  },

  analyzeScene() {
    const { imagePath, selectedScene } = this.data

    if (!imagePath) {
      wx.showToast({
        title: '请先拍照或上传图片',
        icon: 'none'
      })
      return
    }

    this.setData({ analyzing: true })

    setTimeout(() => {
      const report = buildReport(selectedScene, imagePath)

      this.setData({
        analyzing: false,
        report
      })
    }, 1200)
  },

  resetAll() {
    this.setData({
      imagePath: '',
      selectedScene: 'bathroom',
      report: null,
      analyzing: false
    })
  }
})
