(() => {
  'use strict';

  const root = document.querySelector('[data-download-data]');
  if (!root) return;

  const $ = (selector, context = root) => context.querySelector(selector);
  const distroSelect = $('#sorotDistro');
  const detected = $('#sorotDetectedPlatform');
  const status = $('#sorotDistroStatus');
  const releaseList = $('#sorotReleaseList');
  const latestVersion = document.querySelector('#sorotLatestVersion');
  const latestVersionBadge = document.querySelector('#sorotLatestVersionBadge');
  const latestTestReport = document.querySelector('#sorotLatestTestReport');
  if (!distroSelect || !detected || !status || !releaseList) return;

  const OWNER = 'M-TamDre07';
  const REPO = 'Linux-Software-Lab';
  const RAW_ROOT = 'https://raw.githubusercontent.com/' + OWNER + '/' + REPO + '/main';
  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
  const versionPattern = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;
  const filePattern = /^[A-Za-z0-9][A-Za-z0-9._+-]*$/;
  const hashPattern = /^[a-f0-9]{64}$/;
  const formats = new Set(['deb', 'rpm', 'pkg.tar.zst', 'flatpak', 'flatpakref', 'AppImage', 'tar.gz', 'zip', 'whl']);
  const kinds = new Set(['native-package', 'debian-package', 'rpm-package', 'arch-package', 'flatpak-bundle', 'flatpak-ref', 'appimage', 'source-archive', 'python-wheel']);

  const trustedManifestURL = value => {
    if (typeof value !== 'string') return '';
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || url.hostname !== 'raw.githubusercontent.com' ||
          url.port && url.port !== '443' || url.username || url.password || url.search || url.hash) return '';
      if (!new RegExp('^/' + OWNER + '/' + REPO + '/main/apps/[a-z0-9-]+/releases/' +
          '[0-9]+\\.[0-9]+\\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?/release\\.json$').test(url.pathname)) return '';
      return url.href;
    } catch (_) {
      return '';
    }
  };

  const trustedArtifactURL = (value, manifestURL, filename) => {
    const base = new URL('.', manifestURL);
    const expected = new URL(filename, base);
    if (typeof value !== 'string') return '';
    try {
      const actual = new URL(value);
      if (actual.protocol !== 'https:' || actual.hostname !== 'raw.githubusercontent.com' ||
          actual.port && actual.port !== '443' || actual.username || actual.password ||
          actual.search || actual.hash || actual.href !== expected.href) return '';
      return actual.href;
    } catch (_) {
      return '';
    }
  };

  const fallbackDistributions = {
    'debian-family': {
      id: 'debian-family', family: 'debian-family',
      label: 'Debian / Ubuntu dan turunannya', packageFormat: 'deb',
      packageManager: 'apt', sourceFormats: ['tar.gz', 'zip'],
      note: 'Paket .deb hanya ditampilkan bila tercatat dalam manifest rilis yang tervalidasi.'
    },
    arch: {
      id: 'arch', family: 'arch-family',
      label: 'Arch Linux', packageFormat: 'pkg.tar.zst',
      packageManager: 'pacman', sourceFormats: ['tar.gz', 'zip'],
      note: 'Paket Arch belum tercatat pada arsip saat ini.'
    },
    fedora: {
      id: 'fedora', family: 'fedora-family',
      label: 'Fedora / RHEL dan turunannya', packageFormat: 'rpm',
      packageManager: 'dnf', sourceFormats: ['tar.gz', 'zip'],
      note: 'Belum ada paket RPM yang dapat dipilih dari metadata rilis saat ini.'
    },
    opensuse: {
      id: 'opensuse', family: 'suse-family',
      label: 'openSUSE / SUSE', packageFormat: 'rpm',
      packageManager: 'zypper', sourceFormats: ['tar.gz', 'zip'],
      note: 'Belum ada paket RPM yang dapat dipilih dari metadata rilis saat ini.'
    },
    'other-linux': {
      id: 'other-linux', family: 'unknown',
      label: 'Linux lain / distro belum diketahui', packageFormat: null,
      packageManager: null, sourceFormats: ['tar.gz', 'zip'],
      note: 'Pilih distro yang cocok; browser tidak dapat memastikan nama distro Linux secara andal.'
    },
    'non-linux': {
      id: 'non-linux', family: 'unknown',
      label: 'Windows / macOS / sistem non-Linux', packageFormat: null,
      packageManager: null, sourceFormats: ['tar.gz', 'zip'],
      note: 'Sorot adalah aplikasi desktop native Linux; arsip source bukan installer Windows/macOS.'
    }
  };

  const detectOS = () => {
    const platform = String(navigator.userAgentData?.platform || navigator.platform || '');
    const agent = String(navigator.userAgent || '');
    if (/linux/i.test(platform) || /linux/i.test(agent)) return { id: 'other-linux', label: 'Linux' };
    if (/windows/i.test(platform) || /windows/i.test(agent)) return { id: 'non-linux', label: 'Windows' };
    if (/mac/i.test(platform) || /mac os|macintosh/i.test(agent)) return { id: 'non-linux', label: 'macOS' };
    return { id: 'other-linux', label: 'sistem operasi tidak diketahui' };
  };

  const detectedOS = detectOS();
  distroSelect.value = detectedOS.id;
  detected.textContent = detectedOS.label === 'Linux'
    ? 'Browser mengenali Linux, tetapi tidak mengungkap distro secara andal. Pilih distro secara manual; pilihan browser tidak dianggap bukti kompatibilitas.'
    : 'Petunjuk browser: ' + detectedOS.label + '. Pemilih ini hanya mengatur metadata yang ditampilkan, bukan memasang paket secara otomatis.';

  let registry = null;

  const normalizeDistribution = raw => {
    if (!raw || typeof raw.id !== 'string' || typeof raw.label !== 'string' ||
        typeof raw.family !== 'string' || typeof raw.note !== 'string' ||
        !Array.isArray(raw.source_formats)) throw new Error('Invalid distribution entry');
    if (!raw.source_formats.every(value => value === 'tar.gz' || value === 'zip')) {
      throw new Error('Unsupported source format in distribution index');
    }
    return {
      id: raw.id, family: raw.family, label: raw.label,
      packageFormat: raw.package_format || null,
      packageManager: raw.package_manager || null,
      sourceFormats: raw.source_formats, note: raw.note
    };
  };

  const fetchJSON = async (url, maximumBytes = 2 * 1024 * 1024) => {
    const response = await fetch(url, { cache: 'no-cache', redirect: 'error' });
    if (!response.ok) throw new Error('Could not load ' + url);
    const length = Number(response.headers.get('content-length') || 0);
    if (length > maximumBytes) throw new Error('Metadata exceeds the size limit');
    const text = await response.text();
    if (new TextEncoder().encode(text).length > maximumBytes) throw new Error('Metadata exceeds the size limit');
    return JSON.parse(text);
  };

  const normalizeRelease = (manifest, manifestURL, expectedProduct, expectedVersion) => {
    if (!manifest || manifest.schema_version !== 1 ||
        String(manifest.product || '').toLowerCase() !== expectedProduct.id ||
        manifest.version !== expectedVersion ||
        !['stable', 'beta', 'alpha', 'development'].includes(manifest.channel) ||
        !['released', 'testing', 'planned', 'archived'].includes(manifest.status) ||
        !Array.isArray(manifest.artifacts)) throw new Error('Release manifest does not match the index');
    const directory = new URL('.', manifestURL).href;
    const artifacts = manifest.artifacts.map(item => {
      if (!item || typeof item.file !== 'string' || !filePattern.test(item.file) ||
          !kinds.has(item.kind) || !formats.has(item.format) || !hashPattern.test(String(item.sha256 || ''))) {
        throw new Error('Invalid release artifact metadata');
      }
      const resolvedURL = trustedArtifactURL(
        item.download_url || directory + item.file,
        manifestURL,
        item.file
      );
      if (!resolvedURL) throw new Error('Artifact URL is outside its trusted version directory');
      const expectedSuffix = {
        deb: '.deb', rpm: '.rpm', 'pkg.tar.zst': '.pkg.tar.zst',
        flatpak: '.flatpak', flatpakref: '.flatpakref',
        AppImage: '.AppImage', 'tar.gz': '.tar.gz', zip: '.zip', whl: '.whl'
      }[item.format];
      if (!item.file.endsWith(expectedSuffix)) throw new Error('Artifact filename does not match format');
      return {
        file: item.file, kind: item.kind, format: item.format,
        architecture: item.architecture || 'all',
        sha256: item.sha256, url: resolvedURL
      };
    });
    const base = directory;
    return {
      version: manifest.version,
      label: 'Sorot ' + manifest.version + (manifest.channel === 'stable' ? '' : ' ' + manifest.channel.toUpperCase()),
      channel: manifest.channel, status: manifest.status,
      architectureNote: manifest.architecture_note || '',
      manifestUrl: manifestURL,
      checksumsUrl: base + 'SHA256SUMS',
      releaseNotesUrl: manifest.notes_url || '',
      testReportUrl: manifest.test_report_url || '',
      artifacts
    };
  };

  const loadRegistry = async (index, releaseIndex) => {
    if (!index || index.schema_version !== 1 || !Array.isArray(index.distributions) ||
        !Array.isArray(index.products)) throw new Error('Distribution index schema mismatch');
    if (!releaseIndex || releaseIndex.schema_version !== 1 || releaseIndex.product !== 'Sorot' ||
        !Array.isArray(releaseIndex.versions) || !Array.isArray(releaseIndex.planned_targets || [])) {
      throw new Error('Sorot release index schema mismatch');
    }
    const distributions = index.distributions.map(normalizeDistribution);
    const seenDistroIds = new Set();
    for (const distro of distributions) {
      if (seenDistroIds.has(distro.id)) throw new Error('Duplicate distribution ID');
      seenDistroIds.add(distro.id);
    }
    const product = index.products.find(item => item && item.id === 'sorot');
    if (!product) throw new Error('Sorot is missing from the distribution index');
    const refs = releaseIndex.versions.map(reference => {
      if (!reference || !versionPattern.test(String(reference.version || '')) ||
          !['stable', 'testing', 'archived'].includes(reference.status) ||
          !['alpha', 'beta', 'rc', 'stable', 'development'].includes(reference.channel) ||
          !Array.isArray(reference.formats) ||
          !reference.formats.every(format => formats.has(format))) {
        throw new Error('Invalid Sorot version index entry');
      }
      const manifestURL = RAW_ROOT + '/apps/sorot/releases/' + reference.version + '/release.json';
      if (!trustedManifestURL(manifestURL)) throw new Error('Manifest URL is outside the trusted GitHub repository');
      return { ...reference, url: manifestURL };
    });
    if (refs.length > 100) throw new Error('Too many Sorot release versions');
    const versions = await Promise.all(refs.map(async reference => {
      const manifestURL = trustedManifestURL(reference.url);
      const manifest = await fetchJSON(manifestURL);
      if (manifest.status !== reference.status || manifest.channel !== reference.channel) {
        throw new Error('Release status/channel do not match the authoritative index');
      }
      const manifestFormats = Array.isArray(manifest.artifacts)
        ? manifest.artifacts.map(item => item && item.format).sort()
        : [];
      if (JSON.stringify(manifestFormats) !== JSON.stringify(reference.formats.slice().sort())) {
        throw new Error('Release formats do not match the authoritative index');
      }
      return normalizeRelease(manifest, manifestURL, product, reference.version);
    }));
    const targets = (releaseIndex.planned_targets || []).map(target => {
      if (!target || !versionPattern.test(String(target.version || '')) ||
          target.status !== 'planned' || typeof target.note !== 'string' || !target.note.trim()) {
        throw new Error('Invalid planned target metadata');
      }
      const distribution = target.distribution_id
        ? distributions.find(item => item.id === target.distribution_id)
        : distributions.find(item => item.label.toLowerCase() === String(target.distribution || '').toLowerCase());
      if (!distribution) throw new Error('Planned target references an unknown distribution');
      return {
        distribution_id: distribution.id,
        version: target.version,
        status: 'planned',
        note: target.note
      };
    });
    return {
      updatedAt: releaseIndex.updated_at || index.updated_at,
      distributions,
      versions,
      plannedTargets: targets
    };
  };

  const getDistro = () => {
    const raw = registry && registry.distributions.find(item => item.id === distroSelect.value);
    const distro = raw || fallbackDistributions[distroSelect.value] || fallbackDistributions['other-linux'];
    const hasPackage = distro.packageFormat && registry && registry.versions.some(release =>
      release.status !== 'archived' &&
      release.artifacts.some(artifact => artifact.format === distro.packageFormat)
    );
    const plannedTarget = registry && registry.plannedTargets.find(target => target.distribution_id === distro.id);
    let availability;
    if (distro.id === 'non-linux') availability = 'unsupported';
    else if (hasPackage) availability = 'available';
    else if (plannedTarget) availability = 'planned';
    else availability = 'source-only';
    let note = distro.note || '';
    if (availability === 'available') {
      note = 'Tersedia paket ' + '.' + distro.packageFormat + ' di salah satu manifest rilis. Periksa versi, arsitektur, dan status testing sebelum mengunduh.';
    } else if (availability === 'planned' && plannedTarget) {
      note = plannedTarget.note + ' Target ' + plannedTarget.version + ' belum menjadi unduhan.';
    }
    return { ...distro, status: availability, note, plannedTarget };
  };

  const labelForFormat = (format, architecture) => {
    const label = {
      deb: 'PAKET DEBIAN · .DEB',
      'pkg.tar.zst': 'PAKET ARCH · .PKG.TAR.ZST',
      rpm: 'PAKET RPM · .RPM',
      flatpak: 'FLATPAK BUNDLE · .FLATPAK',
      flatpakref: 'FLATPAK REFERENCE · .FLATPAKREF',
      AppImage: 'PORTABLE · .APPIMAGE',
      'tar.gz': 'ARSIP SUMBER · .TAR.GZ',
      zip: 'ARSIP SUMBER · .ZIP',
      whl: 'PYTHON WHEEL · .WHL'
    }[format] || ('FORMAT · ' + String(format).toUpperCase());
    return architecture && !['all', 'any', 'noarch'].includes(architecture)
      ? label + ' · ' + String(architecture).toUpperCase()
      : label;
  };

  const installCommand = (manager, file) => {
    if (!filePattern.test(file)) return '';
    if (manager === 'apt' && file.endsWith('.deb')) return 'sudo apt install ./' + file;
    if (manager === 'pacman' && file.endsWith('.pkg.tar.zst')) return 'sudo pacman -U ./' + file;
    if (manager === 'dnf' && file.endsWith('.rpm')) return 'sudo dnf install ./' + file;
    if (manager === 'zypper' && file.endsWith('.rpm')) return 'sudo zypper install ./' + file;
    return '';
  };

  const artifactMarkup = (artifact, distro) => {
    const source = artifact.kind === 'source-archive' && distro.sourceFormats.includes(artifact.format);
    const pythonWheel = artifact.kind === 'python-wheel' && distro.id !== 'non-linux';
    const native = distro.status === 'available' && artifact.format === distro.packageFormat &&
      !['source-archive', 'python-wheel'].includes(artifact.kind);
    if (!source && !native && !pythonWheel) return '';
    const primary = native ? ' is-primary' : '';
    const title = source ? 'Unduh arsip sumber' : pythonWheel ? 'Unduh Python wheel' : 'Unduh paket instalasi';
    return '<a class="sorot-artifact-link' + primary + '" href="' + escapeHTML(artifact.url) + '">' +
      '<span class="sorot-artifact-format">' + escapeHTML(labelForFormat(artifact.format, artifact.architecture)) + '</span>' +
      '<strong>' + title + '</strong><small>' + escapeHTML(artifact.file) + '</small>' +
      '<span class="sorot-artifact-arrow" aria-hidden="true">↓</span></a>';
  };

  const releaseMarkup = (release, distro) => {
    const links = [
      '<a href="' + escapeHTML(release.checksumsUrl) + '">SHA256SUMS ↗</a>',
      '<a href="' + escapeHTML(release.manifestUrl) + '" target="_blank" rel="noopener noreferrer">Manifest versi ↗</a>',
      release.releaseNotesUrl && /^https:\/\//.test(release.releaseNotesUrl)
        ? '<a href="' + escapeHTML(release.releaseNotesUrl) + '" target="_blank" rel="noopener noreferrer">Catatan rilis ↗</a>' : '',
      release.testReportUrl && /^https:\/\//.test(release.testReportUrl)
        ? '<a href="' + escapeHTML(release.testReportUrl) + '" target="_blank" rel="noopener noreferrer">Laporan pengujian ↗</a>' : ''
    ].filter(Boolean).join('');
    const visibleArtifacts = release.artifacts.map(item => artifactMarkup(item, distro)).filter(Boolean).join('');
    const native = distro.status === 'available'
      ? release.artifacts.find(item => item.format === distro.packageFormat && item.kind !== 'source-archive')
      : null;
    const command = native ? installCommand(distro.packageManager, native.file) : '';
    const note = release.status === 'testing'
      ? 'Rilis ini masih Beta/testing dan bukan rilis stabil.'
      : release.status === 'planned' ? 'Versi ini direncanakan, tetapi bukan unduhan yang tersedia.' : '';
    const commandMarkup = command
      ? '<div class="sorot-install-note"><strong>Instalasi via terminal</strong><code>' + escapeHTML(command) +
        '</code><span>Jalankan dari direktori tempat paket diunduh. Perintah ini tidak membuktikan kompatibilitas yang belum diuji.</span></div>'
      : '';
    return '<article class="sorot-release-card"><div class="sorot-release-heading">' +
      '<div class="sorot-release-brand"><img src="/assets/images/sorot-icon.svg" alt="" width="54" height="54" loading="lazy" decoding="async">' +
      '<div><span class="sorot-release-kicker">VERSI TERARSIP</span><h3>' + escapeHTML(release.label) + '</h3>' +
      '<p>Linux desktop · versi ' + escapeHTML(release.version) + '</p></div></div>' +
      '<span class="sorot-release-status">' + escapeHTML(release.status.toUpperCase()) + ' · ' + escapeHTML(release.channel.toUpperCase()) + '</span></div>' +
      '<p class="sorot-release-notice">' + escapeHTML(note || 'Format yang ditampilkan bersumber dari manifest versi yang terdaftar di GitHub.') +
      ' ' + escapeHTML(release.architectureNote) + '</p>' +
      '<div class="sorot-artifact-grid">' +
      (visibleArtifacts || '<p class="sorot-release-notice">Belum ada format yang cocok untuk pilihan distro ini.</p>') +
      '</div><div class="sorot-release-footer"><span><strong>Integritas:</strong> SHA-256 mendeteksi mismatch terhadap metadata; bukan tanda tangan kriptografis penerbit.</span>' +
      links + '</div>' + commandMarkup + '</article>';
  };

  const render = () => {
    const latest = registry && registry.versions.length
      ? registry.versions[registry.versions.length - 1]
      : null;
    if (latestVersion) latestVersion.textContent = latest
      ? latest.version + ' ' + latest.channel.toUpperCase()
      : 'Memuat indeks versi…';
    if (latestVersionBadge) latestVersionBadge.textContent = latest
      ? latest.channel.toUpperCase() + ' ' + latest.version
      : 'Rilis Beta';
    if (latestTestReport && latest) {
      latestTestReport.href = /^https:\/\//.test(latest.testReportUrl)
        ? latest.testReportUrl : latest.manifestUrl;
    }
    const distro = getDistro();
    status.textContent = distro.note;
    if (!registry) {
      const sourceFormats = distro.sourceFormats || ['tar.gz', 'zip'];
      releaseList.querySelectorAll('.sorot-artifact-link[data-format]').forEach(link => {
        const format = link.dataset.format || '';
        link.hidden = !sourceFormats.includes(format);
      });
      const command = releaseList.querySelector('.sorot-install-note[data-package-format="deb"]');
      if (command) command.hidden = true;
      return;
    }
    const releases = registry.versions.slice().reverse();
    releaseList.innerHTML = releases.length
      ? releases.map(release => releaseMarkup(release, distro)).join('')
      : '<article class="sorot-release-card"><p>Belum ada versi rilis yang terdaftar untuk Sorot.</p></article>';
  };

  distroSelect.addEventListener('change', render);
  render();

  const indexPath = String(root.dataset.downloadData || '');
  if (indexPath === '/data/distribution-index.json') {
    Promise.all([
      fetchJSON(indexPath, 2 * 1024 * 1024),
      fetchJSON(RAW_ROOT + '/apps/sorot/releases/index.json', 1024 * 1024)
    ])
      .then(([distributionIndex, releaseIndex]) => loadRegistry(distributionIndex, releaseIndex))
      .then(value => {
        registry = value;
        render();
      })
      .catch(() => {
        render();
        status.textContent += ' Indeks rilis GitHub tidak dapat dimuat; unduhan paket disembunyikan sampai metadata dapat divalidasi.';
      });
  }
})();