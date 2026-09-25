
#!/bin/bash

set -euo pipefail

sudo apt install git cmake build-essential python3 python3-pip -y
git clone https://github.com/aldebaran/libqi.git
git clone https://github.com/aldebaran/libqi-python.git
pip install conan
conan profile detect || true

QI_VERSION="4.0.5"
cd libqi-python
conan export ../libqi --version "${QI_VERSION}"
conan install . -s build_type=Release --profile=default --build=missing -c tools.build:skip_test=true -c tools.build:jobs=4
cmake --preset conan-linux-x86_64-gcc-release
cmake --build --preset conan-linux-x86_64-gcc-release
PYTHON_LIB_PATH=$(python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))")
cmake --install build/linux-x86_64-gcc-release/ --component Module --prefix "${PYTHON_LIB_PATH}/"
cd ..
pip install opencv-python

# --- Extraire les exports depuis le fichier conanrunenv et les ajouter à ~/.profile ---
# Le script cherche un fichier conanrunenv-*.sh dans le dossier de build, récupère
# les lignes commençant par "export " et les place dans un bloc délimité dans ~/.profile.

BUILD_DIR="./libqi-python/build"
CONAN_RUNENV_FILE=$(find "${BUILD_DIR}" -type f -name 'conanrunenv*.sh' 2>/dev/null | head -n 1 || true)
PROFILE="$HOME/.profile"
PROFILE_MODIFIED=0

if [ -n "${CONAN_RUNENV_FILE}" ] && [ -f "${CONAN_RUNENV_FILE}" ]; then
	echo "Fichier conan runenv trouvé: ${CONAN_RUNENV_FILE}"
	tmpfile=$(mktemp)
	# extraire uniquement les lignes commençant par 'export '
	grep -E '^export[[:space:]]+' "${CONAN_RUNENV_FILE}" > "${tmpfile}" || true

	if [ -s "${tmpfile}" ]; then
		# assurer l'existence du fichier de profil
		if [ ! -f "${PROFILE}" ]; then
			touch "${PROFILE}"
		fi

		ts=$(date +%Y%m%d%H%M%S)
		backup="${PROFILE}.backup.${ts}"
		cp "${PROFILE}" "${backup}" || true

		{
			echo ""
			# coller les exports tels quels
			cat "${tmpfile}"
			echo ""
		} >> "${PROFILE}"

			rm -f "${tmpfile}"
			echo "Les variables d'environnement ont été ajoutées à ${PROFILE} (sauvegarde: ${backup})"

			# Indiquer que le profil a été modifié ; on le rechargera en fin de script.
			PROFILE_MODIFIED=1
	else
		echo "Aucune ligne 'export' trouvée dans ${CONAN_RUNENV_FILE}. Rien à ajouter."
		rm -f "${tmpfile}"
	fi
else
	echo "Aucun fichier conanrunenv trouvé dans ${BUILD_DIR}."
fi

# Recharger ~/.profile à la fin du script uniquement si on l'a modifié.
if [ "${PROFILE_MODIFIED:-0}" -eq 1 ]; then
	echo "~/.profile a été modifié — rechargement dans le shell du script"
	# shellcheck disable=SC1090
	. "${PROFILE}" || true
else
	echo "~/.profile non modifié — pas de rechargement"
fi
