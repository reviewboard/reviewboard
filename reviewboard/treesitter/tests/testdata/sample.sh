#!/bin/bash

# Sample bash script demonstrating various shell features
# Author: ReviewBoard Team
# Description: Development environment setup script

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Constants and configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_NAME="reviewboard"
readonly DEFAULT_PYTHON_VERSION="3.9"
readonly LOG_FILE="/tmp/${PROJECT_NAME}_setup.log"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Global variables
PYTHON_VERSION="${DEFAULT_PYTHON_VERSION}"
VERBOSE=false
DRY_RUN=false
FORCE_REINSTALL=false

# Function definitions
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup development environment for ReviewBoard

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -n, --dry-run          Show what would be done without executing
    -f, --force            Force reinstallation of dependencies
    -p, --python VERSION   Python version to use (default: ${DEFAULT_PYTHON_VERSION})

EXAMPLES:
    $0                      # Basic setup
    $0 -v -p 3.10          # Verbose setup with Python 3.10
    $0 --dry-run           # Preview what would be done

EOF
}

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            if [[ "$VERBOSE" == true ]]; then
                echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE"
            fi
            ;;
    esac

    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit "${2:-1}"
}

# Cleanup function for trap
cleanup() {
    local exit_code=$?
    log "INFO" "Cleaning up temporary files..."

    # Remove temporary files if they exist
    [[ -f "/tmp/setup_temp.txt" ]] && rm -f "/tmp/setup_temp.txt"

    if [[ $exit_code -eq 0 ]]; then
        log "INFO" "Setup completed successfully"
    else
        log "ERROR" "Setup failed with exit code $exit_code"
    fi

    exit $exit_code
}

# Set up signal handlers
trap cleanup EXIT
trap 'error_exit "Script interrupted" 130' INT TERM

# System detection
detect_system() {
    local os_name
    local arch

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        os_name="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        os_name="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        os_name="windows"
    else
        error_exit "Unsupported operating system: $OSTYPE"
    fi

    arch=$(uname -m)

    log "INFO" "Detected system: $os_name ($arch)"
    echo "${os_name}_${arch}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Version comparison function
version_compare() {
    local version1="$1"
    local version2="$2"

    if [[ "$version1" == "$version2" ]]; then
        return 0
    fi

    local IFS=.
    local i ver1=($version1) ver2=($version2)

    # Fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
        ver1[i]=0
    done

    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]} ]]; then
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 2
        fi
    done
    return 0
}

# Check Python installation
check_python() {
    local python_cmd="python${PYTHON_VERSION}"

    log "INFO" "Checking Python ${PYTHON_VERSION} installation..."

    if ! command_exists "$python_cmd"; then
        log "WARN" "Python ${PYTHON_VERSION} not found, trying 'python3'"
        python_cmd="python3"

        if ! command_exists "$python_cmd"; then
            error_exit "Python not found. Please install Python ${PYTHON_VERSION}"
        fi
    fi

    # Check Python version
    local installed_version
    installed_version=$($python_cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')

    version_compare "$installed_version" "$PYTHON_VERSION"
    local result=$?

    if [[ $result -eq 2 ]]; then
        error_exit "Python version $installed_version is too old. Required: ${PYTHON_VERSION}+"
    fi

    log "INFO" "Python $installed_version found at $(which $python_cmd)"
    echo "$python_cmd"
}

# Install dependencies based on system
install_system_dependencies() {
    local system="$1"

    log "INFO" "Installing system dependencies for $system..."

    case "$system" in
        linux_*)
            if command_exists apt-get; then
                log "DEBUG" "Using apt package manager"
                if [[ "$DRY_RUN" == false ]]; then
                    sudo apt-get update
                    sudo apt-get install -y \
                        build-essential \
                        libpq-dev \
                        python3-dev \
                        git \
                        curl \
                        nodejs \
                        npm
                fi
            elif command_exists yum; then
                log "DEBUG" "Using yum package manager"
                if [[ "$DRY_RUN" == false ]]; then
                    sudo yum install -y \
                        gcc \
                        postgresql-devel \
                        python3-devel \
                        git \
                        curl \
                        nodejs \
                        npm
                fi
            else
                error_exit "No supported package manager found"
            fi
            ;;
        macos_*)
            if command_exists brew; then
                log "DEBUG" "Using Homebrew package manager"
                if [[ "$DRY_RUN" == false ]]; then
                    brew install postgresql python node npm
                fi
            else
                log "WARN" "Homebrew not found. Please install dependencies manually."
            fi
            ;;
        windows_*)
            log "WARN" "Windows detected. Please ensure you have the required dependencies installed."
            ;;
    esac
}

# Setup Python virtual environment
setup_virtualenv() {
    local python_cmd="$1"
    local venv_dir="${SCRIPT_DIR}/.venv"

    log "INFO" "Setting up Python virtual environment..."

    if [[ -d "$venv_dir" ]] && [[ "$FORCE_REINSTALL" == false ]]; then
        log "INFO" "Virtual environment already exists"
        return 0
    fi

    if [[ "$DRY_RUN" == false ]]; then
        if [[ -d "$venv_dir" ]]; then
            log "INFO" "Removing existing virtual environment"
            rm -rf "$venv_dir"
        fi

        log "INFO" "Creating virtual environment with $python_cmd"
        "$python_cmd" -m venv "$venv_dir"

        # Activate virtual environment
        # shellcheck source=/dev/null
        source "${venv_dir}/bin/activate"

        # Upgrade pip
        pip install --upgrade pip setuptools wheel
    fi
}

# Install Python dependencies
install_python_dependencies() {
    log "INFO" "Installing Python dependencies..."

    local requirements_files=(
        "${SCRIPT_DIR}/requirements.txt"
        "${SCRIPT_DIR}/dev-requirements.txt"
    )

    for req_file in "${requirements_files[@]}"; do
        if [[ -f "$req_file" ]]; then
            log "DEBUG" "Installing from $req_file"
            if [[ "$DRY_RUN" == false ]]; then
                pip install -r "$req_file"
            fi
        else
            log "WARN" "Requirements file not found: $req_file"
        fi
    done
}

# Setup database
setup_database() {
    log "INFO" "Setting up database..."

    local db_name="${PROJECT_NAME}_dev"
    local db_user="${PROJECT_NAME}_user"

    if command_exists createdb; then
        if [[ "$DRY_RUN" == false ]]; then
            # Check if database exists
            if psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
                log "INFO" "Database $db_name already exists"
            else
                log "INFO" "Creating database $db_name"
                createdb "$db_name"
            fi
        fi
    else
        log "WARN" "PostgreSQL tools not found. Database setup skipped."
    fi
}

# Run tests
run_tests() {
    log "INFO" "Running tests..."

    if [[ "$DRY_RUN" == false ]]; then
        if [[ -f "${SCRIPT_DIR}/manage.py" ]]; then
            python "${SCRIPT_DIR}/manage.py" test
        elif command_exists pytest; then
            pytest
        else
            log "WARN" "No test runner found"
        fi
    fi
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE_REINSTALL=true
                shift
                ;;
            -p|--python)
                PYTHON_VERSION="$2"
                shift 2
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                error_exit "Unexpected argument: $1"
                ;;
        esac
    done
}

# Main setup function
main() {
    log "INFO" "Starting ${PROJECT_NAME} development setup"

    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "DRY RUN MODE - No changes will be made"
    fi

    # Environment setup
    local system
    system=$(detect_system)

    local python_cmd
    python_cmd=$(check_python)

    # Dependency installation
    install_system_dependencies "$system"
    setup_virtualenv "$python_cmd"
    install_python_dependencies

    # Project setup
    setup_database

    # Verification
    run_tests

    log "INFO" "Setup completed successfully!"

    # Print next steps
    cat << EOF

${GREEN}Setup Complete!${NC}

Next steps:
1. Activate the virtual environment:
   ${BLUE}source ${SCRIPT_DIR}/.venv/bin/activate${NC}

2. Start the development server:
   ${BLUE}python manage.py runserver${NC}

3. Visit http://localhost:8000 in your browser

For more information, see the documentation at:
https://example.com/docs/

EOF
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_arguments "$@"
    main
fi
