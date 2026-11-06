/**
 * 63tube プロトタイプ
 * - videos.json / comments.json を読み込み
 * - スワイプで動画切り替え
 * - いいね（localStorage）、コメント表示
 * - 次の動画をプリロード
 */

const API_BASE = '.'; // 同ディレクトリの JSON を使用

let videos = [];
let comments = [];
let currentIndex = 0;
let likes = JSON.parse(localStorage.getItem('63tube_likes') || '{}');

const viewport = document.getElementById('viewport');
const navPrevBtn = document.getElementById('navPrev');
const navNextBtn = document.getElementById('navNext');
const muteBtn = document.getElementById('muteBtn');
const likeBtn = document.getElementById('likeBtn');
const likeCountEl = document.getElementById('likeCount');
const commentInput = document.getElementById('commentInput');
const commentBtn = document.getElementById('commentBtn');
const commentsList = document.getElementById('commentsList');
const currentIdxEl = document.getElementById('currentIdx');
const totalCountEl = document.getElementById('totalCount');
const countdownEl = document.getElementById('countdown');

// 動画プリロード用（前後1本を先読み）
const preloadedVideos = {};

// カウントダウン（卒業日時：2026-11-10 1:00・1秒毎に更新）
function updateCountdown() {
  const gradDate = new Date('2026-11-10T01:00:00+09:00');
  const diff = gradDate - new Date();
  if (diff <= 0) {
    countdownEl.textContent = '卒業おめでとう！🎉';
    return;
  }
  const d = Math.floor(diff / 86400000);
  const h = Math.floor(diff / 3600000) % 24;
  const m = Math.floor(diff / 60000) % 60;
  const s = Math.floor(diff / 1000) % 60;
  const p = (n) => String(n).padStart(2, '0');
  countdownEl.textContent =
    `卒業まであと ${d}日 ${p(h)}:${p(m)}:${p(s)}`;
}

setInterval(updateCountdown, 1000);
updateCountdown();

// JSON 読み込み
async function loadData() {
  try {
    const [vRes, cRes] = await Promise.all([
      fetch(`${API_BASE}/videos.json`),
      fetch(`${API_BASE}/comments.json`)
    ]);
    videos = await vRes.json();
    comments = await cRes.json();
    totalCountEl.textContent = videos.length;
    render(currentIndex);
  } catch (err) {
    console.error('データ読み込みエラー:', err);
    viewport.innerHTML = '<div class="loading">データの読み込みに失敗しました<br>ローカルサーバーで動かしてください</div>';
  }
}

// HEVC(HDR)対応判定 — 非対応端末はSDRフォールバックへ
function pickUrl(v) {
  if (!v.url_sd) return v.url;
  const ok = document.createElement('video')
    .canPlayType('video/mp4; codecs="hvc1.1.6.L150.B0"');
  return ok === 'probably' ? v.url : v.url_sd;
}

// スライド描画（ループ対応・プリロード再利用）
function render(index) {
  // ループ処理：最初から前へ→最後へ、最後から次へ→最初へ
  if (index < 0) index = videos.length - 1;
  if (index >= videos.length) index = 0;
  currentIndex = index;

  const video = videos[index];
  viewport.innerHTML = '';

  const slide = document.createElement('div');
  slide.className = 'slide';
  slide.dataset.id = video.id;

  // 撮影日（右上に独立表示）
  const dateEl = document.createElement('div');
  dateEl.className = 'video-date';
  dateEl.textContent = video.date;
  slide.appendChild(dateEl);

  const wrapper = document.createElement('div');
  wrapper.className = 'video-wrapper';

  // プリロード済みの video 要素を使い回し（裏でキャッシュ済み）
  let vid = preloadedVideos[index];
  if (!vid) {
    vid = document.createElement('video');
    vid.src = pickUrl(video);
    vid.playsInline = true;
    vid.setAttribute('webkit-playsinline', '');
    vid.setAttribute('playsinline', '');
    vid.setAttribute('muted', '');
    vid.controls = false;
    vid.preload = 'auto';
    vid.style.width = '100%';
    vid.style.height = '100%';
    vid.style.objectFit = 'cover';
    vid.style.display = 'block';
    vid.style.pointerEvents = 'none'; // iOS で video タップを完全に無効化
    preloadedVideos[index] = vid;
  } else {
    vid.pause();
    vid.currentTime = 0;
  }

  // 横向き動画を縦スマホに合わせて回転
  if (video.orientation === 'landscape') {
    vid.className = 'landscape';
    vid.style.transform = 'rotate(90deg)';
    vid.style.width = '100%';
    vid.style.height = '100%';
    vid.style.objectFit = 'cover';
  } else {
    vid.className = '';
    vid.style.transform = '';
    vid.style.width = '100%';
    vid.style.height = '100%';
    vid.style.objectFit = 'cover';
  }

  // 自動再生を試みる（iOS は muted + ユーザー操作が必要な場合がある）
  const savedSound = localStorage.getItem('63tube_sound_on');
  vid.muted = savedSound !== 'true';
  muteBtn.textContent = vid.muted ? '🔇' : '🔊';
  muteBtn.classList.toggle('muted', vid.muted);
  vid.play().catch(() => {
    // 自動再生ブロックされた場合は、タップで再生を待つ
  });

  // タップで再生/一時停止切り替え
  let isPlaying = false;
  wrapper.addEventListener('click', (e) => {
    e.stopPropagation();
    if (isPlaying) {
      vid.pause();
    } else {
      vid.play().catch(() => {
        vid.muted = true;
        vid.play();
      });
    }
    isPlaying = !isPlaying;
  });

  vid.addEventListener('play', () => { isPlaying = true; });
  vid.addEventListener('pause', () => { isPlaying = false; });
  // 終了したら自動で次の動画へ（ループ）
  vid.addEventListener('ended', () => { isPlaying = false; render(currentIndex + 1); });

  wrapper.appendChild(vid);
  slide.appendChild(wrapper);

  const info = document.createElement('div');
  info.className = 'video-info';
  info.innerHTML = `
    <div class="title">${escapeHtml(video.title)}</div>
    <div class="meta">${escapeHtml(video.cast)} • ${video.duration}秒</div>
  `;
  wrapper.appendChild(info);  // 動画下部にオーバーレイ（コメント欄と重ならない）

  viewport.appendChild(slide);

  // いいね状態を反映
  updateLikeUI(video.id);

  // コメント描画
  renderComments(video.id);

  // プリロード（前後）
  preload(index - 1);
  preload(index + 1);

  currentIdxEl.textContent = currentIndex + 1;
}

// プリロード（裏で次の動画を先読み・キャッシュ）
function preload(index) {
  if (index < 0 || index >= videos.length) return;
  if (preloadedVideos[index]) return;
  const v = videos[index];
  const vid = document.createElement('video');
  vid.src = pickUrl(v);
  vid.playsInline = true;
  vid.setAttribute('webkit-playsinline', '');
  vid.setAttribute('playsinline', '');
  vid.setAttribute('muted', '');
  vid.controls = false;
  vid.preload = 'auto';
  vid.style.width = '100%';
  vid.style.height = '100%';
  vid.style.objectFit = 'cover';
  vid.style.display = 'block';
  vid.style.pointerEvents = 'none';
  preloadedVideos[index] = vid;
  // 読み込み開始（ブラウザがキャッシュを確保）
  vid.load();
}

// いいね
function updateLikeUI(videoId) {
  const liked = likes[videoId] || 0;
  likeCountEl.textContent = liked;
  likeBtn.classList.toggle('liked', liked > 0);
}

muteBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  const vidEl = viewport.querySelector('video');
  if (!vidEl) return;
  vidEl.muted = !vidEl.muted;
  localStorage.setItem('63tube_sound_on', vidEl.muted ? 'false' : 'true');
  muteBtn.textContent = vidEl.muted ? '🔇' : '🔊';
  muteBtn.classList.toggle('muted', vidEl.muted);
  if (!vidEl.muted && vidEl.paused) vidEl.play();
});

likeBtn.addEventListener('click', () => {
  const video = videos[currentIndex];
  likes[video.id] = (likes[video.id] || 0) + 1;
  localStorage.setItem('63tube_likes', JSON.stringify(likes));
  updateLikeUI(video.id);
  spawnHearts();
});

function spawnHearts() {
  const rect = likeBtn.getBoundingClientRect();
  for (let i = 0; i < 5; i++) {
    const heart = document.createElement('div');
    heart.className = 'like-explosion';
    heart.textContent = ['❤️', '💖', '💗', '💓'][Math.floor(Math.random() * 4)];
    heart.style.left = (rect.left + rect.width / 2 + (Math.random() - 0.5) * 40) + 'px';
    heart.style.top = (rect.top + rect.height / 2 + (Math.random() - 0.5) * 40) + 'px';
    document.body.appendChild(heart);
    setTimeout(() => heart.remove(), 600);
  }
}

// コメント
function renderComments(videoId) {
  commentsList.innerHTML = '';
  const list = comments.filter(c => c.video_id === videoId);
  list.forEach(c => {
    const el = document.createElement('div');
    el.className = 'comment-item';
    el.innerHTML = `
      <span class="nickname">${escapeHtml(c.nickname)}</span>
      <span class="body">${escapeHtml(c.body)}</span>
      <span class="time">${new Date(c.created_at).toLocaleString('ja-JP', {month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit'})}</span>
    `;
    commentsList.appendChild(el);
  });
  commentsList.scrollTop = commentsList.scrollHeight;
}

commentBtn.addEventListener('click', addComment);
commentInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') addComment();
});

function addComment() {
  const text = commentInput.value.trim();
  if (!text) return;
  const video = videos[currentIndex];
  const newComment = {
    video_id: video.id,
    nickname: '名無しのPさん',
    body: text,
    created_at: new Date().toISOString()
  };
  comments.unshift(newComment);
  commentInput.value = '';
  renderComments(video.id);
}

// スワイプ処理
let touchStartX = 0;
let touchStartY = 0;
let isSwiping = false;

viewport.addEventListener('touchstart', (e) => {
  touchStartX = e.touches[0].clientX;
  touchStartY = e.touches[0].clientY;
  isSwiping = true;
}, { passive: true });

viewport.addEventListener('touchmove', (e) => {
  if (!isSwiping) return;
  const dx = e.touches[0].clientX - touchStartX;
  const dy = e.touches[0].clientY - touchStartY;
  // 縦スワイプが主（上下スワイプで切り替え）
  const slide = viewport.querySelector('.slide');
  if (slide) {
    // 軽い追従（任意）
    slide.style.transform = `translateY(${dy * 0.3}px)`;
  }
  // Android Chrome でブラウザのデフォルトスクロールを抑制
  if (Math.abs(dy) > 10) {
    e.preventDefault();
  }
}, { passive: false });

viewport.addEventListener('touchend', (e) => {
  if (!isSwiping) {
    isSwiping = false;
    return;
  }
  const dx = e.changedTouches[0].clientX - touchStartX;
  const dy = e.changedTouches[0].clientY - touchStartY;

  // 上スワイプ → 次へ、下スワイプ → 前へ（閾値 80px）
  const slide = viewport.querySelector('.slide');
  if (slide) slide.style.transform = '';

  if (Math.abs(dy) > 80 && Math.abs(dy) > Math.abs(dx)) {
    if (dy < 0) {
      // 上にスワイプ → 次の動画
      render(currentIndex + 1);
    } else {
      // 下にスワイプ → 前の動画
      render(currentIndex - 1);
    }
  }
  isSwiping = false;
});

// ナビゲーションボタン（Mac/iPad などスワイプできない環境用）
navPrevBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  render(currentIndex - 1);
});

navNextBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  render(currentIndex + 1);
});

// マウスホイールで動画切り替え（Mac など）
let wheelTimeout = null;
viewport.addEventListener('wheel', (e) => {
  e.preventDefault();
  if (wheelTimeout) return;
  wheelTimeout = setTimeout(() => {
    wheelTimeout = null;
  }, 500);
  
  if (e.deltaY < 0) {
    // ホイール上 → 次の動画
    render(currentIndex + 1);
  } else {
    // ホイール下 → 前の動画
    render(currentIndex - 1);
  }
}, { passive: false });

// HTML エスケープ
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// 起動
loadData();