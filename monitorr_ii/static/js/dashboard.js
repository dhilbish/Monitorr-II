/* Monitorr-II dashboard: polls /api/services and /api/system, swaps partials in. */
(function () {
    const M = window.MONITORR || {};
    const BASE = M.basePath || '';
    const RF_SVC = Math.max(5000, M.rfsysinfo || 30000);
    const RF_SYS = Math.max(5000, M.rftime || 30000);
    let svcTimer, sysTimer;

    function loadServices() {
        fetch(`${BASE}/api/services`).then(r => r.text()).then(html => {
            document.getElementById('statusloop').innerHTML = html;
            $('.pace-activity').addClass('hidepace');
            $('.modalloadingindex').addClass('hidemodal');
        }).catch(() => {});
    }
    function loadSystem() {
        fetch(`${BASE}/api/system`).then(r => r.text()).then(html => {
            document.getElementById('stats').innerHTML = html;
        }).catch(() => {});
    }

    function startTimers() {
        svcTimer = setInterval(loadServices, RF_SVC);
        sysTimer = setInterval(loadSystem, RF_SYS);
    }
    function stopTimers() {
        clearInterval(svcTimer); clearInterval(sysTimer);
    }

    $(function () {
        loadServices();
        loadSystem();
        startTimers();

        const toggle = document.getElementById('autorefresh');
        if (toggle) {
            toggle.addEventListener('change', () => {
                if (toggle.checked) startTimers();
                else stopTimers();
            });
        }

        // simple digital time display alongside the analog clock
        function tick() {
            const d = new Date();
            const hours = M.time24h ? d.getHours() : ((d.getHours() % 12) || 12);
            const ampm = M.time24h ? '' : (d.getHours() >= 12 ? ' PM' : ' AM');
            const pad = n => String(n).padStart(2, '0');
            const time = `${pad(hours)}:${pad(d.getMinutes())}:${pad(d.getSeconds())}${ampm}`;
            const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
            const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            const datePart = `${days[d.getDay()]} | ${months[d.getMonth()]} ${pad(d.getDate())}<br>${d.getFullYear()}`;
            const html = `<div class="dtg">${time}</div><div id="line">__________</div><div class="date">${datePart}</div>`;
            const t = document.getElementById('timer');
            if (t) t.innerHTML = html;
        }
        tick();
        setInterval(tick, 1000);
    });
})();
