(() => {
'use strict';

const root = document.querySelector('[data-download-data]');
if (!root) return;

const $ = (selector, context = root) => context.querySelector(selector);
const distroSelect = $('#sorotDistro');
const detected = $('#sorotDetectedPlatform');
const status = $('#sorotDistroStatus');
const releaseList = $('#sorotReleaseList');
if (!distroSelect || !detected || !status || !releaseList) return;

const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));

const safeHTTPS = value => {
  try {
    const url = new URL(String(value || ''));
    return url.protocol === 'https:' ? url.href : '';
  } catch (_) {
    return '';
  }
};

const fallbackDistributions = {
  'debian-family': {
    label: 'Debian / Ubuntu dan turunannya', status: 'available', packageFormat: 'deb',
    packageManager: 'apt', sourceFormats: ['tar.gz', 'zip'],
    note: 'Paket .deb Sorot 0.5.0 Beta tersedia; instalasi bersih Debian 13 belum dinyatakan terverifikasi.'
  },
  arch: {
    label: 'Arch Linux', status: 'planned', packageFormat: 'pkg.tar.zst',
    packageManager: 'pacman', sourceFormats: ['tar.gz', 'zip'], targetVersion: '0.6.0',
    note: 'Paket Arch ditargetkan untuk Sorot 0.6.0. Belum ada paket Arch yang dipublikasikan.'
  },
  fedora: {
    label: 'Fedora / RHEL dan turunannya', status: 'source-only', packageFormat: 'rpm',
    packageManager: 'dnf', sourceFormats: ['tar.gz', 'zip'],
    note: 'Belum ada paket RPM yang dipublikasikan.'
  },
  opensuse: {
    label: 'openSUSE / SUSE', status: 'source-only', packageFormat: 'rpm',
    packageManager: 'zypper', sourceFormats: ['tar.gz', 'zip'],
    note: 'Belum ada paket RPM yang dipublikasikan.'
  },
  'other-linux': {
    label: 'Linux lain / distro belum diketahui', status: 'source-only',
    packageFormat: null, packageManager: null, sourceFormats: ['tar.gz', 'zip'],
    note: 'Tampilkan arsip sumber saja; belum ada paket native yang dinyatakan cocok.'
  },
  'non-linux': {
    label: 'Windows / macOS / sistem non-Linux', status: 'unsupported',
    packageFormat: null, packageManager: null, sourceFormats: ['tar.gz', 'zip'],
    note: 'Sorot adalah aplikasi native Linux. Arsip sumber bukan installer Windows/macOS.'
  }
};

const detectOSFamily = () => {
  const platform = String(navigator.userAgentData?.platform || navigator.platform || '');
  const agent = String(navigator.userAgent || '');
  if (/linux/i.test(platform) || /linux/i.test(agent)) return { id: 'other-linux', label: 'Linux' };
  if (/windows/i.test(platform) || /windows/i.test(agent)) return { id: 'non-linux', label: 'Windows' };
  if (/mac/i.test(platform) || /mac os|macintosh/i.test(agent)) return { id: 'non-linux', label: 'macOS' };
  return { id: 'other-linux', label: 'sistem operasi tidak diketahui' };
};

const detectedOS = detectOSFamily();
distroSelect.value = detectedOS.id;
detected.textContent = detectedOS.label === 'Linux'
  ? 'Browser mengenali OS sebagai Linux, tetapi tidak mengungkap nama distro secara andal. Pilih distro secara manual; pilihan browser tidak dijadikan bukti kompatibilitas.'
  : 'Petunjuk browser: ' + detectedOS.label + '. Pemilih ini tidak menginstal apa pun otomatis; pilih distro target hanya jika memang sedang mengunduh untuk sistem tersebut.';

let data = null;

const getDistro = () => {
  if (!data || !Array.isArray(data.distributions)) return fallbackDistributions[distroSelect.value] || fallbackDistributions['other-linux'];
  return data.distributions.find(item => item.id === distroSelect.value) || fallbackDistributions['other-linux'];
};

const labelForFormat = format => ({
  deb: 'PAKET DEBIAN · .DEB',
  'pkg.tar.zst': 'PAKET ARCH · .PKG.TAR.ZST',
  rpm: 'PAKET RPM · .RPM',
  'tar.gz': 'ARSIP SUMBER · .TAR.GZ',
  zip: 'ARSIP SUMBER · .ZIP'
}[format] || ('FORMAT · ' + String(format).toUpperCase()));

const commandFor = (manager, filename) => {
  const safeName = String(filename || '');
  if (!/^[A-Za-z0-9._+-]+$/.test(safeName)) return '';
  if (manager === 'apt' && safeName.endsWith('.deb')) return 'sudo apt install ./' + safeName;
  if (manager === 'pacman' && safeName.endsWith('.pkg.tar.zst')) return 'sudo pacman -U ./' + safeName;
  if (manager === 'dnf' && safeName.endsWith('.rpm')) return 'sudo dnf install ./' + safeName;
  if (manager === 'zypper' && safeName.endsWith('.rpm')) return 'sudo zypper install ./' + safeName;
  return '';
};

const artifactMarkup = (artifact, distro) => {
  const file = escapeHTML(artifact.file);
  const format = String(artifact.format || '');
  const isSource = artifact.kind === 'source-archive' && (distro.sourceFormats || []).includes(format);
  const isNativePackage = distro.status === 'available' && format === distro.packageFormat;
  if (!isSource && !isNativePackage) return '';
  const href = safeHTTPS(artifact.url);
  if (!href || !file) return '';
  const primary = isNativePackage ? ' is-primary' : '';
  let title = 'Unduh arsip sumber';
  if (format === 'deb') title = 'Unduh paket instalasi';
  if (format === 'pkg.tar.zst') title = 'Unduh paket Arch';
  if (format === 'rpm') title = 'Unduh paket RPM';
  return '<a class="sorot-artifact-link' + primary + '" href="' + escapeHTML(href) + '">' +
    '<span class="sorot-artifact-format">' + escapeHTML(labelForFormat(format)) + '</span>' +
    '<strong>' + escapeHTML(title) + '</strong>' +
    '<small>' + file + '</small><span class="sorot-artifact-arrow" aria-hidden="true">↓</span></a>';
};

const releaseMarkup = (release, distro) => {
  const artifacts = Array.isArray(release.artifacts) ? release.artifacts : [];
  const visibleArtifacts = artifacts.map(artifact => artifactMarkup(artifact, distro)).filter(Boolean).join('');
  const nativeArtifact = distro.status === 'available' ? artifacts.find(item => item.format === distro.packageFormat) : null;
  const command = nativeArtifact ? commandFor(distro.packageManager, nativeArtifact.file) : '';
  const note = release.status === 'testing'
    ? 'Versi ini masih beta/testing dan bukan rilis stabil.'
    : 'Periksa catatan rilis dan pengujian untuk versi ini.';
  const checksumURL = safeHTTPS(release.checksumsUrl);
  const manifestURL = safeHTTPS(release.manifestUrl);
  const notesURL = safeHTTPS(release.releaseNotesUrl);
  const testsURL = safeHTTPS(release.testReportUrl);
  const links = [
    checksumURL ? '<a href="' + escapeHTML(checksumURL) + '">SHA256SUMS ↗</a>' : '',
    manifestURL ? '<a href="' + escapeHTML(manifestURL) + '" target="_blank" rel="noopener noreferrer">Manifest versi ↗</a>' : '',
    notesURL ? '<a href="' + escapeHTML(notesURL) + '" target="_blank" rel="noopener noreferrer">Catatan rilis ↗</a>' : '',
    testsURL ? '<a href="' + escapeHTML(testsURL) + '" target="_blank" rel="noopener noreferrer">Laporan pengujian ↗</a>' : ''
  ].filter(Boolean).join('');
  const commandSection = command
    ? '<div class="sorot-install-note"><strong>Instalasi via terminal</strong><code>' + escapeHTML(command) + '</code><span>Jalankan dari direktori tempat paket diunduh. Perintah ini tidak menjadikan paket beta sebagai rilis stabil dan tidak membuktikan kompatibilitas yang belum diuji.</span></div>'
    : '';
  return '<article class="sorot-release-card">' +
    '<div class="sorot-release-heading"><div class="sorot-release-brand"><img src="/assets/images/sorot-icon.svg" alt="" width="54" height="54" loading="lazy" decoding="async"><div>' +
    '<span class="sorot-release-kicker">VERSI TERARSIP</span><h3>' + escapeHTML(release.label || ('Sorot ' + release.version)) + '</h3>' +
    '<p>Linux desktop · Python / PySide6</p></div></div><span class="sorot-release-status">' +
    escapeHTML(String(release.status || 'unknown').toUpperCase()) + ' · ' + escapeHTML(String(release.channel || '').toUpperCase()) + '</span></div>' +
    '<p class="sorot-release-notice">' + escapeHTML(note) + ' ' + escapeHTML(release.architectureNote || '') + '</p>' +
    '<div class="sorot-artifact-grid">' + (visibleArtifacts || '<p class="sorot-release-notice">Tidak ada artefak yang cocok untuk distribusi ini pada versi tersebut.</p>') + '</div>' +
    '<div class="sorot-release-footer"><span><strong>Integritas:</strong> verifikasi checksum sebelum instalasi. SHA-256 tidak sama dengan tanda tangan penerbit.</span>' + links + '</div>' +
    commandSection + '</article>';
};

const render = () => {
  const distro = getDistro();
  const versions = data && Array.isArray(data.versions) ? data.versions : [];
  const supportAvailable = distro.status === 'available' && (data
    ? versions.some(release => Array.isArray(release.artifacts) && release.artifacts.some(artifact => artifact.format === distro.packageFormat))
    : Boolean(root.querySelector('.sorot-artifact-link[data-format="' + distro.packageFormat + '"]'))
  );
  let message = distro.note || '';
  if (distro.status === 'available' && !supportAvailable) {
    message = 'Metadata menyatakan format ini tersedia, tetapi tidak ada artefak versi yang cocok. Jangan gunakan tautan paket sampai metadata diperbaiki.';
  } else if (distro.status === 'available' && supportAvailable) {
    message += ' Website akan menampilkan paket native yang tercatat pada manifest dan arsipnya.';
  } else if (distro.status === 'planned') {
    message += ' Ini target pengembangan, bukan unduhan yang sudah tersedia.';
  }
  status.textContent = message;

  if (data && versions.length) {
    releaseList.innerHTML = versions.slice().reverse().map(release => releaseMarkup(release, distro)).join('');
  } else {
    const sourceFormats = distro.sourceFormats || ['tar.gz', 'zip'];
    releaseList.querySelectorAll('.sorot-artifact-link[data-format]').forEach(link => {
      const format = link.dataset.format || '';
      link.hidden = !(sourceFormats.includes(format) || (distro.status === 'available' && format === distro.packageFormat));
    });
    const command = releaseList.querySelector('.sorot-install-note[data-package-format="deb"]');
    if (command) command.hidden = !(distro.status === 'available' && distro.packageFormat === 'deb');
  }
};

distroSelect.addEventListener('change', render);
render();

const dataPath = String(root.dataset.downloadData || '');
if (dataPath.startsWith('/data/') && !dataPath.includes('..')) {
  fetch(dataPath, { cache: 'no-cache' })
    .then(response => {
      if (!response.ok) throw new Error('Download metadata unavailable');
      return response.json();
    })
    .then(payload => {
      if (!payload || payload.schemaVersion !== 1 || payload.product !== 'Sorot' ||
          !Array.isArray(payload.distributions) || !Array.isArray(payload.versions)) {
        throw new Error('Download metadata schema mismatch');
      }
      data = payload;
      render();
    })
    .catch(() => {
      render();
      status.textContent += ' Metadata dinamis tidak dapat dimuat; kartu fallback tetap digunakan.';
    });
}
})();
