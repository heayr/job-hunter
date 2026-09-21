// ==========================================
// Job Hunter CRM — Backend API Client
// ==========================================

window.api = {
    async getPitches() {
        const res = await fetch('/api/pitches');
        if (!res.ok) throw new Error(`Failed to load pitches: ${res.status}`);
        return await res.json();
    },

    async updateVacancyStatus(vacId, status, reason = null) {
        const res = await fetch(`/api/vacancies/${encodeURIComponent(vacId)}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, reason })
        });
        if (!res.ok) throw new Error(`Failed to update status: ${res.status}`);
        return await res.json();
    },

    async getShameList() {
        const res = await fetch('/api/shame_list');
        if (!res.ok) throw new Error(`Failed to load shame list: ${res.status}`);
        return await res.json();
    },

    async rewriteAI(vacId) {
        const res = await fetch(`/api/vacancies/${encodeURIComponent(vacId)}/rewrite`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error(`Failed to rewrite AI pitch: ${res.status}`);
        return await res.json();
    },

    rewriteAIStream(vacId, callbacks) {
        const { onProgress, onChunk, onDone, onError } = callbacks;
        const eventSource = new EventSource(`/api/vacancies/${encodeURIComponent(vacId)}/rewrite-stream`);

        eventSource.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data);
            if (onProgress) onProgress(data);
        });

        eventSource.addEventListener('chunk', (e) => {
            const data = JSON.parse(e.data);
            if (onChunk) onChunk(data);
        });

        eventSource.addEventListener('done', (e) => {
            const data = JSON.parse(e.data);
            eventSource.close();
            if (onDone) onDone(data);
        });

        eventSource.addEventListener('error', (e) => {
            let data;
            try { data = JSON.parse(e.data); } catch { data = { message: 'SSE connection error' }; }
            eventSource.close();
            if (onError) onError(data);
        });

        eventSource.onerror = () => {
            eventSource.close();
            if (onError) onError({ message: 'Network error — check VPN and server' });
        };

        return eventSource;
    },

    async ratePitch(vacId, rating, pitchType = null, shortDm = null, coverLetter = null) {
        const res = await fetch('/api/pitches/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vacancy_id: vacId,
                rating,
                pitch_type: pitchType,
                short_dm: shortDm,
                cover_letter: coverLetter
            })
        });
        if (!res.ok) throw new Error(`Failed to rate pitch: ${res.status}`);
        return await res.json();
    },

    async savePitch(vacId, shortDm = null, coverLetter = null) {
        const res = await fetch('/api/pitches/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vacancy_id: vacId,
                short_dm: shortDm,
                cover_letter: coverLetter
            })
        });
        if (!res.ok) throw new Error(`Failed to save pitch: ${res.status}`);
        return await res.json();
    },

    async getProfiles() {
        const res = await fetch('/api/profiles');
        if (!res.ok) throw new Error(`Failed to load profiles: ${res.status}`);
        return await res.json();
    },

    async saveProfiles(profilesData) {
        const res = await fetch('/api/profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profilesData)
        });
        if (!res.ok) throw new Error(`Failed to save profiles: ${res.status}`);
        return await res.json();
    },

    async uploadResume(filename, base64) {
        const res = await fetch('/api/upload_resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, base64 })
        });
        if (!res.ok) throw new Error(`Failed to upload resume: ${res.status}`);
        return await res.json();
    },

    async getConfig() {
        const res = await fetch('/api/config');
        if (!res.ok) throw new Error(`Failed to load config: ${res.status}`);
        return await res.json();
    },

    async saveConfig(configData) {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });
        if (!res.ok) throw new Error(`Failed to save config: ${res.status}`);
        return await res.json();
    },

    async startHarvest(sources, limit) {
        const res = await fetch('/api/harvest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sources, limit })
        });
        return res;
    },

    async getHarvestStatus() {
        const res = await fetch('/api/harvest/status');
        if (!res.ok) throw new Error(`Failed to get harvest status: ${res.status}`);
        return await res.json();
    },

    async getEnrichStatus() {
        const res = await fetch('/api/harvest/enrich/status');
        if (!res.ok) throw new Error(`Failed to get enrich status: ${res.status}`);
        return await res.json();
    },

    async parseVacancyAi(payload) {
        const res = await fetch('/api/vacancies/ai-parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(`AI parse failed: ${res.status}`);
        return await res.json();
    },

    async getCdpStatus() {
        try {
            const res = await fetch('/api/agent/cdp/status');
            return await res.json();
        } catch (e) {
            return { success: false, cdp_available: false };
        }
    },

    async launchCdp() {
        const res = await fetch('/api/agent/cdp/launch', { method: 'POST' });
        return await res.json();
    },

    async post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`POST ${url} failed: ${res.status}`);
        return await res.json();
    }
};

var api = window.api;
