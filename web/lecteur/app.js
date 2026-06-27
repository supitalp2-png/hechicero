// 1) Charger le JSON
async function loadData() {
    const response = await fetch("data.json");
    return await response.json();
}

// 2) Fonction pour afficher un écran
function render(screenHtml) {
    document.getElementById("app").innerHTML = screenHtml;
}

// 3) Navigation simple
function goTo(screen, params = {}) {
    screens[screen](params);
}

// 3b) Animation de sélection de jaquette (agrandissement + ouverture, UX < 200ms)
function selectCard(el, screen, params) {
    el.classList.add('podcast--selected');
    setTimeout(() => goTo(screen, params), 150);
}

// 4) Définition des écrans (on les remplira plus tard)
const screens = {
    accueil: () => {
        render(`
            <div class="screen">
                <h1>Hechicero</h1>
                <button onclick="goTo('choixPodcast')">Entrer</button>
            </div>
        `);
    },

    choixPodcast: async () => {
        const data = await loadData();

        let html = `<div class="screen"><h2>Choix du podcast</h2>`;

        data.podcasts.forEach(p => {
            html += `
                <div class="podcast" onclick="selectCard(this, 'choixChapitre', { id: '${p.id}' })">
                    <img src="${p.image}">
                    <p>${p.titre}</p>
                </div>
            `;
        });

        html += `</div>`;
        render(html);
    },

    choixChapitre: async ({ id }) => {
        const data = await loadData();
        const podcast = data.podcasts.find(p => p.id === id);

        let html = `<div class="screen"><h2>${podcast.titre}</h2>`;

        podcast.chapitres.forEach(c => {
            html += `
                <div class="chapitre" onclick="goTo('lecture', { id: '${id}', chapitre: '${c.id}' })">
                    <p>${c.titre}</p>
                </div>
            `;
        });

        html += `</div>`;
        render(html);
    },

    lecture: async ({ id, chapitre }) => {
        const data = await loadData();
        const podcast = data.podcasts.find(p => p.id === id);
        const chap = podcast.chapitres.find(c => c.id === chapitre);

        render(`
            <div class="screen lecture">
                <img class="cover" src="${podcast.image}">
                <h3>${chap.titre}</h3>
                <audio controls autoplay src="${chap.audio}"></audio>
                <button onclick="goTo('pause', { id: '${id}', chapitre: '${chapitre}' })">Pause</button>
            </div>
        `);
    },

    pause: async ({ id, chapitre }) => {
        const data = await loadData();
        const podcast = data.podcasts.find(p => p.id === id);
        const chap = podcast.chapitres.find(c => c.id === chapitre);

        render(`
            <div class="screen pause">
                <img class="cover" src="${podcast.image}">
                <div class="pause-overlay">II</div>
                <h3>${chap.titre}</h3>
                <button onclick="goTo('lecture', { id: '${id}', chapitre: '${chapitre}' })">Reprendre</button>
            </div>
        `);
    }
};

// 5) Lancer l’écran d’accueil
goTo("accueil");
