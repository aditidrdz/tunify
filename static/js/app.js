/* =====================================================================
   Tunify — Spotify-style same-artist recommendation system (frontend)

   Playback pipeline (audio-only, no embedded video):
     1. Click song -> GET /api/play/<id>
     2. Backend uses yt-dlp to extract a direct YouTube CDN audio URL
     3. Frontend feeds that URL to a hidden HTML5 <audio> element
     4. If extraction fails, automatically falls back to iTunes 30s preview
   ===================================================================== */

const state = {
  songsById: new Map(),
  homeSongs: [],
  artists: [],
  current: null,
  queue: [],
  isPlaying: false,
  searchActive: false,
  playSeq: 0,  // monotonic counter so out-of-order /api/play responses are ignored
  currentView: "home",  // "home" | "liked" | "search" | "artist"
  likes: new Map(),     // id -> full song object (persisted to localStorage)
};

/* ---------- Likes (server-backed, per-user) ---------- */

// Legacy localStorage key from earlier versions — migrated on first login.
const LEGACY_LIKES_KEY = "tunify_likes_v1";

// Keep a parallel lookup by "title|artist" so we can find a like even after
// iTunes-cache restarts give the same song a different negative id.
function _likeKey(song) {
  return `${(song.title || "").toLowerCase()}|${(song.artist || "").toLowerCase()}`;
}

function isLiked(songId) {
  if (state.likes.has(songId)) return true;
  const song = state.songsById.get(songId);
  if (!song) return false;
  const key = _likeKey(song);
  for (const liked of state.likes.values()) {
    if (_likeKey(liked) === key) return true;
  }
  return false;
}

async function fetchLikesFromServer() {
  try {
    const r = await fetch("/api/likes");
    if (!r.ok) return new Map();
    const arr = await r.json();
    return new Map(arr.map((s) => [s.id, s]));
  } catch {
    return new Map();
  }
}

async function migrateLegacyLikes() {
  try {
    const raw = localStorage.getItem(LEGACY_LIKES_KEY);
    if (!raw) return;
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr) || !arr.length) {
      localStorage.removeItem(LEGACY_LIKES_KEY);
      return;
    }
    console.log(`Migrating ${arr.length} liked songs to your account…`);
    for (const song of arr) {
      try {
        await fetch("/api/likes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(song),
        });
      } catch {}
    }
    localStorage.removeItem(LEGACY_LIKES_KEY);
  } catch (err) {
    console.warn("legacy likes migration failed", err);
  }
}

async function toggleLike(song) {
  if (!song || song.id === undefined) return;

  // Resolve an existing like (which may live under a different id but same key)
  const key = _likeKey(song);
  let existingId = state.likes.has(song.id) ? song.id : null;
  if (existingId === null) {
    for (const [id, liked] of state.likes) {
      if (_likeKey(liked) === key) { existingId = id; break; }
    }
  }

  if (existingId !== null) {
    // UN-like: optimistic remove + server DELETE
    state.likes.delete(existingId);
    refreshLikeButtons(song.id, false);
    updateLikedCountBadge();
    if (state.currentView === "liked") renderLikedView();
    try {
      await fetch(
        `/api/likes/${existingId}?title=${encodeURIComponent(song.title)}&artist=${encodeURIComponent(song.artist)}`,
        { method: "DELETE" }
      );
    } catch (err) { console.warn(err); }
  } else {
    // LIKE: clean payload + optimistic add
    const payload = {
      id: song.id,
      title: song.title,
      artist: song.artist,
      album: song.album,
      year: song.year,
      duration: song.duration,
      color: song.color,
      artwork_url: song.artwork_url,
      preview_url: song.preview_url,
      external: !!song.external,
    };
    state.likes.set(song.id, payload);
    refreshLikeButtons(song.id, true);
    updateLikedCountBadge();
    if (state.currentView === "liked") renderLikedView();
    try {
      await fetch("/api/likes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (err) { console.warn(err); }
  }
}

function refreshLikeButtons(songId, animate = false) {
  const liked = isLiked(songId);
  document.querySelectorAll(`[data-like-id="${songId}"]`).forEach((btn) => {
    btn.classList.toggle("liked", liked);
    btn.textContent = liked ? "♥" : "♡";
    btn.title = liked ? "Remove from liked songs" : "Add to liked songs";
    if (animate) {
      btn.classList.remove("like-just-liked");
      // Force reflow to restart animation
      void btn.offsetWidth;
      btn.classList.add("like-just-liked");
    }
  });
  // Player heart-button stays hidden until a song is playing
  if (state.current && state.current.id === songId) {
    const pb = $("player-like-btn");
    pb.hidden = false;
  }
}

function updateLikedCountBadge() {
  const el = $("liked-count");
  if (el) el.textContent = state.likes.size;
}

function likeButtonHTML(song, variant = "card") {
  const cls =
    variant === "card" ? "like-btn-card" :
    variant === "mini" ? "like-btn-mini" :
    "like-btn-player";
  const liked = isLiked(song.id);
  const icon = liked ? "♥" : "♡";
  const title = liked ? "Remove from liked songs" : "Add to liked songs";
  return `<button class="${cls} ${liked ? "liked" : ""}" data-like-id="${song.id}" title="${title}">${icon}</button>`;
}

/** Attach click handlers to every like-btn inside `root` (delegated). */
function wireLikeButtons(root) {
  root.querySelectorAll("[data-like-id]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(btn.dataset.likeId);
      const song = state.songsById.get(id) || state.likes.get(id);
      if (song) toggleLike(song);
    });
  });
}

// Single HTML5 audio element — used for both YouTube-extracted streams
// and iTunes 30s preview fallback.
const audio = new Audio();
audio.preload = "auto";

/* ---------- helpers ---------- */

const $ = (id) => document.getElementById(id);

function secToMMSS(t) {
  if (!isFinite(t) || t < 0) return "0:00";
  t = Math.floor(t);
  const m = Math.floor(t / 60);
  const sec = t % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function gradient(color) {
  return `linear-gradient(135deg, ${color}, ${shade(color, -45)})`;
}
function shade(hex, percent) {
  const num = parseInt((hex || "#1ed760").replace("#", ""), 16);
  const r = Math.max(0, Math.min(255, ((num >> 16) & 0xff) + percent));
  const g = Math.max(0, Math.min(255, ((num >> 8) & 0xff) + percent));
  const b = Math.max(0, Math.min(255, (num & 0xff) + percent));
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

function letter(s) {
  return (s?.[0] || "♪").toUpperCase();
}

function indexSongs(songs) {
  for (const s of songs) state.songsById.set(s.id, s);
}

function coverInner(song) {
  if (song.artwork_url) {
    return `<img src="${escapeHtml(song.artwork_url)}" alt="${escapeHtml(song.title)}" loading="lazy"
              onerror="this.replaceWith(Object.assign(document.createElement('span'),{textContent:'${letter(song.title)}'}))" />`;
  }
  return `<span>${letter(song.title)}</span>`;
}
function coverStyle(song) {
  return `background: ${gradient(song.color)};`;
}

/* ---------- API ---------- */

async function fetchSongs(q = "") {
  const url = q ? `/api/songs?q=${encodeURIComponent(q)}` : "/api/songs";
  const r = await fetch(url);
  return r.json();
}
async function fetchArtists() {
  const r = await fetch("/api/artists");
  return r.json();
}
async function fetchRecommendations(songId) {
  const r = await fetch(`/api/recommend/${songId}`);
  return r.json();
}
async function fetchPlayInfo(songId) {
  const r = await fetch(`/api/play/${songId}`);
  return r.json();
}

/* ---------- Rendering ---------- */

function renderSongsGrid(songs) {
  indexSongs(songs);
  const grid = $("songs-grid");
  $("all-songs-count").textContent =
    `${songs.length} song${songs.length === 1 ? "" : "s"}`;

  if (!songs.length) {
    grid.innerHTML = `
      <div class="muted" style="grid-column: 1/-1; padding: 28px 4px;">
        No songs found. Try a different artist or song name.
      </div>`;
    return;
  }

  grid.innerHTML = songs
    .map(
      (s) => `
    <div class="song-card" data-id="${s.id}">
      <div class="cover" style="${coverStyle(s)}">
        ${coverInner(s)}
        <div class="play-overlay">▶</div>
        ${s.external ? '<div class="ext-badge" title="From iTunes catalog">iTunes</div>' : ""}
        ${likeButtonHTML(s, "card")}
      </div>
      <div class="title" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</div>
      <div class="artist" title="${escapeHtml(s.artist)}">${escapeHtml(s.artist)}</div>
    </div>`
    )
    .join("");

  grid.querySelectorAll(".song-card").forEach((card) => {
    card.addEventListener("click", () => playSong(Number(card.dataset.id)));
  });
  wireLikeButtons(grid);
}

function renderArtists(artists) {
  const ul = $("artist-list");
  ul.innerHTML = artists
    .map(
      (a) => `
    <li data-artist="${escapeHtml(a.name)}">
      <span>${escapeHtml(a.name)}</span>
      <span class="count">${a.count}</span>
    </li>`
    )
    .join("");

  ul.querySelectorAll("li").forEach((li) => {
    li.addEventListener("click", () => {
      const name = li.dataset.artist;
      const filtered = state.homeSongs.filter((s) => s.artist === name);
      $("all-songs-title").textContent = `Songs by ${name}`;
      renderSongsGrid(filtered);
      scrollMainTo(0);
    });
  });
}

function renderHero(song) {
  if (!song) return;
  const cover = $("hero-cover");
  cover.style.background = gradient(song.color);
  cover.innerHTML = coverInner(song);
  $("hero-eyebrow").textContent = "Now Playing";
  $("hero-title").textContent = song.title;
  $("hero-meta").innerHTML = `
    <strong>${escapeHtml(song.artist)}</strong> · ${escapeHtml(song.album || "")} · ${song.year || "—"}
    <span id="hero-status"></span>
  `;
  $("now-artist").innerHTML = `Recommendations from <strong>${escapeHtml(song.artist)}</strong>`;
}

function setHeroStatus(html) {
  const el = $("hero-status");
  if (el) el.innerHTML = html ? " · " + html : "";
}

function renderQueue(rec) {
  const list = $("queue-list");
  $("recs-section").hidden = false;
  $("recs-title").textContent = `Up Next — More from ${rec.artist}`;

  let html = "";
  if (rec.same_artist.length) {
    html += `<div class="queue-divider">More from ${escapeHtml(rec.artist)}</div>`;
    html += rec.same_artist.map((s, i) => queueRow(s, i + 1)).join("");
  } else {
    html += `<div class="queue-divider">No more songs by ${escapeHtml(rec.artist)}</div>`;
  }

  list.innerHTML = html;
  list.querySelectorAll(".queue-row").forEach((row) => {
    row.addEventListener("click", () => playSong(Number(row.dataset.id)));
  });
  wireLikeButtons(list);
  $("queue-count").textContent = state.queue.length;
}

function queueRow(s, idx) {
  indexSongs([s]);
  const isCurrent = state.current && state.current.id === s.id;
  return `
    <div class="queue-row ${isCurrent ? "playing" : ""}" data-id="${s.id}">
      <div class="q-num">${isCurrent ? "♪" : idx}</div>
      <div class="q-cover" style="${coverStyle(s)}">${coverInner(s)}</div>
      <div>
        <div class="q-title">${escapeHtml(s.title)}</div>
        <div class="q-artist">${escapeHtml(s.artist)}</div>
      </div>
      <div class="q-album">${escapeHtml(s.album || "")}</div>
      ${likeButtonHTML(s, "mini")}
      <div class="q-dur">${s.duration}</div>
    </div>`;
}

function renderPlayer(song) {
  $("player").hidden = false;
  const pc = $("player-cover");
  pc.style.background = gradient(song.color);
  pc.innerHTML = coverInner(song);
  $("player-title").textContent = song.title;
  $("player-artist").textContent = song.artist;
  $("dur-time").textContent = song.duration || "—";
  $("cur-time").textContent = "0:00";
  $("bar-fill").style.width = "0%";

  // Player heart button — reflects the current song's liked state
  const pb = $("player-like-btn");
  pb.hidden = false;
  pb.dataset.likeId = String(song.id);
  pb.classList.toggle("liked", isLiked(song.id));
  pb.textContent = isLiked(song.id) ? "♥" : "♡";
  pb.title = isLiked(song.id) ? "Remove from liked songs" : "Add to liked songs";
}

/* ---------- Slide-in Queue Panel ---------- */

function qpRow(song, idx, isCurrent = false) {
  return `
    <div class="qp-row ${isCurrent ? "current" : ""}" data-id="${song.id}">
      <div class="qp-num">${isCurrent ? "♪" : idx}</div>
      <div class="qp-cover" style="${coverStyle(song)}">${coverInner(song)}</div>
      <div class="qp-meta">
        <div class="qp-title">${escapeHtml(song.title)}</div>
        <div class="qp-artist">${escapeHtml(song.artist)}</div>
      </div>
      ${likeButtonHTML(song, "mini")}
      <div class="qp-dur">${song.duration}</div>
    </div>`;
}

function renderQueuePanel() {
  const cur = $("qp-current");
  const next = $("qp-next-list");
  const countEl = $("qp-next-count");

  if (state.current) {
    cur.innerHTML = qpRow(state.current, "♪", true);
  } else {
    cur.innerHTML = `<div class="qp-empty">No song playing yet.</div>`;
  }

  if (state.queue.length) {
    next.innerHTML = state.queue
      .map((s, i) => qpRow(s, i + 1, false))
      .join("");
    countEl.textContent = state.queue.length;
  } else {
    next.innerHTML = `<div class="qp-empty">Nothing else queued. Pick a song to start a same-artist queue.</div>`;
    countEl.textContent = "";
  }

  // Re-wire click handlers
  $("queue-panel").querySelectorAll(".qp-row").forEach((row) => {
    row.addEventListener("click", () => {
      const id = Number(row.dataset.id);
      // If clicked song is already in queue, drop everything before it
      const idx = state.queue.findIndex((s) => s.id === id);
      if (idx > 0) state.queue.splice(0, idx);
      playSong(id);
    });
  });
  wireLikeButtons($("queue-panel"));
}

function openQueuePanel() {
  const p = $("queue-panel");
  p.hidden = false;
  // Force a reflow so the transform transition runs from the hidden state.
  // eslint-disable-next-line no-unused-expressions
  p.offsetHeight;
  p.classList.add("open");
  renderQueuePanel();
}

function closeQueuePanel() {
  $("queue-panel").classList.remove("open");
}

function toggleQueuePanel() {
  const p = $("queue-panel");
  if (p.classList.contains("open")) closeQueuePanel();
  else openQueuePanel();
}

/* ---------- Audio playback (single <audio> element) ---------- */

audio.addEventListener("loadedmetadata", () => {
  $("dur-time").textContent = secToMMSS(audio.duration);
});
audio.addEventListener("timeupdate", () => {
  if (!audio.duration) return;
  $("bar-fill").style.width = `${(audio.currentTime / audio.duration) * 100}%`;
  $("cur-time").textContent = secToMMSS(audio.currentTime);
});
audio.addEventListener("ended", () => playNext());
audio.addEventListener("play", () => {
  state.isPlaying = true;
  $("play-btn").textContent = "❚❚";
});
audio.addEventListener("pause", () => {
  state.isPlaying = false;
  $("play-btn").textContent = "▶";
});
audio.addEventListener("error", () => {
  console.warn("audio error", audio.error);
  // If the YouTube CDN URL failed (expired/blocked), try iTunes preview.
  if (state.current && state.current.preview_url && audio.src !== state.current.preview_url) {
    setHeroStatus('<span style="color:#f59e0b">YouTube unavailable — playing 30-second preview</span>');
    audio.src = state.current.preview_url;
    audio.play().catch(() => {});
  } else {
    setHeroStatus('<span style="color:#f87171">playback failed — skipping</span>');
    setTimeout(() => playNext(), 1200);
  }
});

async function playSong(songId) {
  let song = state.songsById.get(songId);
  if (!song) return;

  // If this is a liked iTunes song whose session-cached negative ID is stale
  // (e.g. after a server restart), call /api/rediscover to get a fresh record.
  if (song.id < 0 && song.external) {
    try {
      const probe = await fetch(`/api/play/${song.id}`);
      if (probe.status === 404) {
        const r = await fetch(
          `/api/rediscover?title=${encodeURIComponent(song.title)}&artist=${encodeURIComponent(song.artist)}`
        );
        if (r.ok) {
          const fresh = await r.json();
          if (fresh && fresh.id !== undefined) {
            // Swap the stale id everywhere it's referenced
            const wasLiked = state.likes.delete(song.id);
            song = fresh;
            state.songsById.set(song.id, song);
            if (wasLiked) {
              state.likes.set(song.id, song);
              saveLikes();
            }
            songId = song.id;
          }
        }
      }
    } catch (err) {
      console.warn("rediscover failed", err);
    }
  }

  state.current = song;
  const seq = ++state.playSeq;

  renderHero(song);
  renderPlayer(song);

  // Fire recommendations request in parallel (don't block playback)
  fetchRecommendations(songId).then((rec) => {
    if (seq !== state.playSeq) return;
    if (rec.queue) indexSongs(rec.queue);
    state.queue = rec.queue || [];
    renderQueue(rec);
    renderQueuePanel();
  });

  // Refresh the queue panel with the new "current" immediately
  renderQueuePanel();

  setHeroStatus('<span style="color:#9ca3af">finding audio…</span>');

  let info;
  try {
    info = await fetchPlayInfo(songId);
  } catch (err) {
    console.warn("fetchPlayInfo failed", err);
    info = null;
  }

  // A newer click happened before this resolved — abandon.
  if (seq !== state.playSeq) return;

  const src = (info && info.audio_url) || song.preview_url;
  if (!src) {
    setHeroStatus('<span style="color:#f59e0b">no audio available — skipping</span>');
    setTimeout(() => playNext(), 1200);
    return;
  }

  if (info && info.audio_url) {
    setHeroStatus("");
  } else {
    setHeroStatus('<span style="color:#f59e0b">YouTube unavailable — playing 30-second preview</span>');
  }

  audio.src = src;
  try {
    await audio.play();
  } catch (err) {
    console.warn("autoplay blocked", err);
  }
}

function playNext() {
  if (!state.queue.length) {
    audio.pause();
    return;
  }
  const next = state.queue.shift();
  $("queue-count").textContent = state.queue.length;
  renderQueuePanel();
  playSong(next.id);
}

function playPrev() {
  audio.currentTime = 0;
  if (audio.src) audio.play().catch(() => {});
}

function togglePlay() {
  if (!state.current) return;
  if (audio.paused) audio.play().catch(() => {});
  else audio.pause();
}

/* ---------- Scrolling helper ---------- */

function scrollMainTo(top) {
  const main = document.querySelector(".main");
  if (main) main.scrollTo({ top, behavior: "smooth" });
}

/* ---------- Wire up controls ---------- */

// ===== Mobile sidebar drawer =================================================
function openDrawer() {
  document.querySelector(".app")?.classList.add("drawer-open");
  const bd = document.getElementById("drawer-backdrop");
  if (bd) { bd.hidden = false; requestAnimationFrame(() => bd.classList.add("open")); }
}
function closeDrawer() {
  document.querySelector(".app")?.classList.remove("drawer-open");
  const bd = document.getElementById("drawer-backdrop");
  if (bd) {
    bd.classList.remove("open");
    setTimeout(() => { bd.hidden = true; }, 250);
  }
}
function toggleDrawer() {
  const app = document.querySelector(".app");
  if (app?.classList.contains("drawer-open")) closeDrawer();
  else openDrawer();
}

function wireControls() {
  $("play-btn").addEventListener("click", togglePlay);
  $("next-btn").addEventListener("click", playNext);
  $("prev-btn").addEventListener("click", playPrev);

  // Hamburger menu (mobile)
  document.getElementById("menu-btn")?.addEventListener("click", toggleDrawer);
  document.getElementById("drawer-backdrop")?.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDrawer();
  });

  document.querySelector(".bar").addEventListener("click", (e) => {
    if (!state.current || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.currentTime = audio.duration * pct;
  });

  $("clear-queue").addEventListener("click", () => {
    state.queue = [];
    $("queue-count").textContent = "0";
    $("recs-section").hidden = true;
    renderQueuePanel();
  });

  // Queue panel
  $("queue-btn").addEventListener("click", toggleQueuePanel);
  $("queue-panel-close").addEventListener("click", closeQueuePanel);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeQueuePanel();
  });

  let searchTimer = null;
  let searchSeq = 0;
  const input = $("search-input");
  const grid = $("songs-grid");

  async function runSearch(q) {
    const seq = ++searchSeq;
    if (q) {
      grid.innerHTML = `
        <div class="muted" style="grid-column: 1/-1; padding: 28px 4px;">
          Searching iTunes for "${escapeHtml(q)}"…
        </div>`;
      $("all-songs-count").textContent = "";
      $("recs-section").hidden = true;
      state.searchActive = true;
      $("all-songs-title").textContent = `Search: "${q}"`;
      scrollMainTo(0);
    } else {
      state.searchActive = false;
      $("all-songs-title").textContent = "All Songs";
      if (state.queue.length) $("recs-section").hidden = false;
    }

    const songs = await fetchSongs(q);
    if (seq !== searchSeq) return;
    renderSongsGrid(songs);
  }

  input.addEventListener("input", (e) => {
    const q = e.target.value.trim();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(q), 250);
  });

  document.querySelectorAll(".nav-item").forEach((b) => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      if (b.dataset.view === "home") {
        state.currentView = "home";
        $("all-songs-title").textContent = "All Songs";
        renderSongsGrid(state.homeSongs);
        $("search-input").value = "";
        state.searchActive = false;
        if (state.queue.length) $("recs-section").hidden = false;
        scrollMainTo(0);
      } else if (b.dataset.view === "search") {
        $("search-input").focus();
      } else if (b.dataset.view === "liked") {
        renderLikedView();
        scrollMainTo(0);
      }
      closeDrawer();
    });
  });

  // Player bar heart button
  $("player-like-btn").addEventListener("click", () => {
    if (state.current) toggleLike(state.current);
  });
}

/* ---------- Liked Songs view ---------- */

function renderLikedView() {
  state.currentView = "liked";
  state.searchActive = false;
  $("recs-section").hidden = true;
  $("search-input").value = "";
  $("all-songs-title").textContent = "Liked Songs";

  // Make sure every liked song is also in songsById so playSong() can find it
  for (const song of state.likes.values()) {
    if (!state.songsById.has(song.id)) state.songsById.set(song.id, song);
  }

  const songs = Array.from(state.likes.values()).reverse(); // most recently liked first
  renderSongsGrid(songs);
}

/* ---------- Init ---------- */

(async function init() {
  // One-time migration: move any leftover localStorage likes into the
  // logged-in user's server-side liked songs.
  await migrateLegacyLikes();

  // Fetch likes from the server (the source of truth for this user)
  state.likes = await fetchLikesFromServer();
  for (const song of state.likes.values()) state.songsById.set(song.id, song);
  updateLikedCountBadge();

  const [songs, artists] = await Promise.all([fetchSongs(), fetchArtists()]);
  state.homeSongs = songs;
  state.artists = artists;
  indexSongs(songs);
  renderSongsGrid(songs);
  renderArtists(artists);
  wireControls();
})();
