const SCENE_MAP = {
  bathroom: {
    label: '卫生间',
    summary: '地面湿滑、缺少扶手和夜间照明是卫生间最常见的跌倒风险。',
    risks: [
      {
        title: '湿滑地砖易摔倒',
        level: '高风险',
        advice: '改用防滑地砖或增加防滑垫，并保持地面及时干燥。'
      },
      {
        title: '马桶和淋浴区缺少扶手',
        level: '高风险',
        advice: '在马桶侧边、淋浴区安装 L 型或一字扶手，辅助起身和站稳。'
      },
      {
        title: '夜间照明不足',
        level: '中风险',
        advice: '增加感应夜灯，减少老人夜起时摸黑行走。'
      }
    ],
    upgrades: [
      '优先改造地面防滑和扶手，这是最关键的两项。',
      '淋浴区建议改成坐式淋浴，降低久站风险。',
      '门槛尽量做平整处理，方便助行器和轮椅通行。'
    ]
  },
  bedroom: {
    label: '卧室',
    summary: '卧室重点关注起夜路径、床边支撑和物品收纳的便利性。',
    risks: [
      {
        title: '床边到卫生间路线杂乱',
        level: '高风险',
        advice: '清理杂物和电线，保证夜间行走路径通畅。'
      },
      {
        title: '床体过高或过低',
        level: '中风险',
        advice: '调整床面高度到膝盖附近，方便老人起身。'
      },
      {
        title: '缺少起夜照明',
        level: '中风险',
        advice: '在床底、墙角或过道安装人体感应灯。'
      }
    ],
    upgrades: [
      '床边可增加助起扶手，降低起身吃力的风险。',
      '常用物品放在伸手可及的位置，减少弯腰和踮脚。',
      '衣柜门把手建议更换为易抓握样式。'
    ]
  },
  livingroom: {
    label: '客厅',
    summary: '客厅常见隐患集中在地毯翘边、家具尖角和通行空间不足。',
    risks: [
      {
        title: '地毯或垫子边缘翘起',
        level: '高风险',
        advice: '固定地毯边缘，或移除容易绊脚的装饰垫。'
      },
      {
        title: '茶几和家具尖角碰撞风险高',
        level: '中风险',
        advice: '给尖角加装防撞条，尽量选择圆角家具。'
      },
      {
        title: '通道过窄',
        level: '中风险',
        advice: '重新调整家具摆放，预留足够转身和助行空间。'
      }
    ],
    upgrades: [
      '沙发旁可预留扶手或稳定支撑点，帮助站起。',
      '电视柜、边柜尽量贴墙，减少动线障碍。',
      '地面颜色对比可更明显，帮助视力退化老人辨识边界。'
    ]
  },
  kitchen: {
    label: '厨房',
    summary: '厨房要优先规避滑倒、烫伤和弯腰取物等高频风险。',
    risks: [
      {
        title: '地面油水易打滑',
        level: '高风险',
        advice: '及时清理水渍油渍，并在高频区域加防滑处理。'
      },
      {
        title: '常用炊具位置过高或过低',
        level: '中风险',
        advice: '把高频物品放在胸口到腰部之间，减少弯腰和抬手。'
      },
      {
        title: '灶台附近缺少紧急操作提醒',
        level: '中风险',
        advice: '增加明显的燃气和电器安全提示，便于老人记忆。'
      }
    ],
    upgrades: [
      '可选缓降橱柜和大号拉手，提高开关便利性。',
      '建议准备防烫手套和稳定的带靠背操作椅。',
      '洗菜区和灶台区域照明要更充足。'
    ]
  },
  corridor: {
    label: '走廊/玄关',
    summary: '走廊和玄关是老人频繁经过的区域，地面平整和扶手尤为重要。',
    risks: [
      {
        title: '鞋物杂乱影响通行',
        level: '高风险',
        advice: '保持通道整洁，鞋柜收纳避免堆放在地面。'
      },
      {
        title: '换鞋缺少稳定支撑',
        level: '中风险',
        advice: '设置带扶手换鞋凳，方便坐下和起身。'
      },
      {
        title: '照明和墙面引导不足',
        level: '中风险',
        advice: '增加过道灯带和醒目的门框、台阶边缘提示。'
      }
    ],
    upgrades: [
      '长走廊可以局部增加连续扶手。',
      '门口高差尽量做无障碍过渡。',
      '雨天区域建议增加吸水防滑垫并固定边缘。'
    ]
  }
}

function buildReport(sceneKey, imagePath) {
  const scene = SCENE_MAP[sceneKey] || SCENE_MAP.livingroom

  return {
    sceneKey,
    sceneLabel: scene.label,
    imagePath,
    score: getSafetyScore(sceneKey),
    summary: scene.summary,
    risks: scene.risks,
    upgrades: scene.upgrades
  }
}

function getSafetyScore(sceneKey) {
  const scoreMap = {
    bathroom: 58,
    bedroom: 71,
    livingroom: 68,
    kitchen: 62,
    corridor: 65
  }

  return scoreMap[sceneKey] || 68
}

module.exports = {
  SCENE_MAP,
  buildReport
}
