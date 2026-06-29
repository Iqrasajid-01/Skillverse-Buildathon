const API_BASE = '/api'

const api = {
  async getScenarios() {
    try {
      const response = await fetch(`${API_BASE}/scenarios`)
      return response.json()
    } catch (error) {
      throw new Error('Failed to fetch scenarios')
    }
  },

  async processScenario(scenarioId, startDay = 1, days = 7) {
    try {
      const response = await fetch(`${API_BASE}/process/${scenarioId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_day: startDay, days })
      })
      return response.json()
    } catch (error) {
      throw new Error('Failed to process scenario')
    }
  },

  async getRun(runId) {
    try {
      const response = await fetch(`${API_BASE}/run/${runId}`)
      return response.json()
    } catch (error) {
      throw new Error('Failed to fetch run')
    }
  },

  async compare(scenarioData) {
    try {
      const response = await fetch(`${API_BASE}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenarioData)
      })
      return response.json()
    } catch (error) {
      throw new Error('Failed to compare')
    }
  },

  async validate(data) {
    try {
      const response = await fetch(`${API_BASE}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      return response.json()
    } catch (error) {
      throw new Error('Failed to validate')
    }
  },

  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE}/health`)
      return response.json()
    } catch (error) {
      return { status: 'offline' }
    }
  }
}

export default api
