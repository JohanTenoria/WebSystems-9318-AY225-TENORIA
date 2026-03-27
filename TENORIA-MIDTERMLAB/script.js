document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('games-container');
    const genreFilter = document.getElementById('genre-filter');

    let gamesData = [];

    // Set current date in footer
    const today = new Date();
    const formattedDate = today.toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' });
    const dateSpan = document.getElementById('update-date');
    if (dateSpan) dateSpan.textContent = formattedDate;

    fetch('data.json')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            gamesData = data;
            populateGenreFilter(gamesData);
            displayGames(gamesData);
        })
        .catch(error => {
            console.error('Error loading data:', error);
            container.innerHTML = '<div class="no-results">⚠️ Failed to load game data. Please run the scraper first.</div>';
        });

    function populateGenreFilter(data) {
        const genres = [...new Set(data.map(game => game.Genre).filter(g => g))];
        genres.sort();
        genres.forEach(genre => {
            const option = document.createElement('option');
            option.value = genre;
            option.textContent = genre;
            genreFilter.appendChild(option);
        });
    }

    function displayGames(data) {
        const selectedGenre = genreFilter.value;
        const filtered = selectedGenre === 'all' ? data : data.filter(game => game.Genre === selectedGenre);

        if (filtered.length === 0) {
            container.innerHTML = '<div class="no-results">✨ No games found for this genre.</div>';
            return;
        }

        container.innerHTML = filtered.map(game => `
            <div class="card">
                <div class="card-content">
                    <span class="genre-badge">${escapeHtml(game.Genre) || 'Unknown'}</span>
                    <h3>${escapeHtml(game['Game Title'])}</h3>
                    
                    <div class="game-details">
                        <div class="game-detail">
                            <strong>📅 Release Date:</strong> ${escapeHtml(game['Release Date'])}
                        </div>
                        <div class="game-detail">
                            <strong>🎮 Platforms:</strong> ${escapeHtml(game['Platform Availability'])}
                        </div>
                        <div class="game-detail">
                            <strong>👨‍💻 Developer:</strong> ${escapeHtml(game['Developer Information'])}
                        </div>
                        <div class="game-detail">
                            <strong>✨ Key Features:</strong> ${escapeHtml(game['Key Features'])}
                        </div>
                    </div>
                    
                    <div class="articles-section">
                        <h4>📰 Articles (${game.Articles ? game.Articles.length : 0})</h4>
                        <div class="articles-list">
                            ${renderArticles(game.Articles)}
                        </div>
                    </div>
                    
                    <div class="game-link">
                        <a href="${escapeHtml(game['Game URL'])}" target="_blank" rel="noopener noreferrer">
                            View game hub →
                        </a>
                    </div>
                </div>
            </div>
        `).join('');
    }

    function renderArticles(articles) {
        if (!articles || articles.length === 0) {
            return '<div class="article-item">No articles found for this game.</div>';
        }
        
        return articles.map(article => `
            <div class="article-item">
                <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" class="article-title">
                    ${escapeHtml(article.title)}
                </a>
                ${article.category && article.category !== 'Not Available' ? `
                    <div class="article-category">${escapeHtml(article.category)}</div>
                ` : ''}
                <div class="article-meta">
                    <span class="article-publisher">${escapeHtml(article.publisher || article.author || 'Unknown')}</span>
                    ${article.date && article.date !== 'Not Available' ? `
                        <span class="article-date">${escapeHtml(article.date)}</span>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    genreFilter.addEventListener('change', () => displayGames(gamesData));

    function escapeHtml(str) {
        if (!str) return 'Not Available';
        if (typeof str !== 'string') return str;
        return str.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }
});