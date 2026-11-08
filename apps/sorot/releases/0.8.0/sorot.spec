# Dihasilkan oleh scripts/build-rpm.sh dari packaging/rpm/sorot.spec.in. Sunting templatnya, bukan hasilnya.
# Sasaran: Fedora 40+ (python3-pyside6 tersedia dari repositori Fedora). Paket noarch murni Python.
%{!?_metainfodir:%global _metainfodir %{_datadir}/metainfo}
%{!?python3:%global python3 %{__python3}}
%{!?python3_sitelib:%global python3_sitelib %(%{python3} -c "import sysconfig; print(sysconfig.get_path('purelib', vars={'base': '/usr', 'platbase': '/usr'}))")}

# The generated python3dist(pyside6-essentials) requirement is not provided under that name by Fedora's
# python3-pyside6; the explicit Requires below is the real dependency.
%global __requires_exclude ^python3[.0-9]*dist\\(pyside6.*$

Name:           sorot
Version:        0.8.0
Release:        1%{?dist}
Summary:        Transparent teleprompter overlay for speaking and recording
License:        MIT
URL:            https://github.com/M-TamDre07/Linux-Software-Lab/tree/main/apps/sorot
Source0:        sorot-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-build
BuildRequires:  python3-installer
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
Requires:       python3 >= 3.11
Requires:       python3-pyside6
Recommends:     python3-keyring
Recommends:     qt6-qtwayland
Suggests:       rclone
Suggests:       python3-pypdf

%description
Sorot shows your script in a transparent window that scrolls at the pace you speak,
above other applications, so you can read while recording or presenting. Scripts and
settings stay on your computer and the application works fully offline. Optional
features (AI rewriting through an API you configure, Google Drive through your own
rclone remote) run only when you use them. Overlay abilities differ between X11 and
Wayland compositors; see the compatibility notes in the documentation.

%prep
%autosetup -n sorot-%{version}

%build
%{python3} -m build --wheel --no-isolation

%install
%{python3} -m installer --destdir=%{buildroot} --prefix=%{_prefix} dist/*.whl
sed -i '1s|^#!.*|#!%{_bindir}/python3|' %{buildroot}%{_bindir}/sorot  # installer writes the build interpreter's path
./scripts/install-files.sh --layout arch %{buildroot} %{_prefix}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/sorot.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/sorot.metainfo.xml || :

%files
%license %{_datadir}/licenses/sorot/LICENSE
%doc %{_docdir}/sorot
%{_bindir}/sorot
%{python3_sitelib}/sorot
%{python3_sitelib}/sorot-%{version}.dist-info
%{_datadir}/applications/sorot.desktop
%{_datadir}/icons/hicolor/*/apps/sorot.*
%{_metainfodir}/sorot.metainfo.xml
%{_mandir}/man1/sorot.1*
%{_datadir}/sorot

%changelog
* Fri Nov 06 2026 Muhammad Andreatama <muhammadandreatama@outlook.com> - 0.8.0-1
- Rilis 0.8.0; lihat CHANGELOG.md di dokumentasi paket.
