#!/usr/bin/env python3
"""
Generate README.md from ecosystem.json configuration.

This script reads ecosystem.json and generates a beautiful README.md
with live data from GitHub repositories.
"""

import json
import os
import sys
import requests
from datetime import datetime
from typing import Dict, List, Any

def get_repo_data(repo_name: str, github_token: str) -> Dict[str, Any]:
    """Fetch repository data from GitHub API."""
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # Get basic repo info
        repo_url = f'https://api.github.com/repos/{repo_name}'
        response = requests.get(repo_url, headers=headers)
        response.raise_for_status()
        repo_data = response.json()
        
        # Get latest release if exists
        releases_url = f'https://api.github.com/repos/{repo_name}/releases/latest'
        try:
            release_response = requests.get(releases_url, headers=headers)
            if release_response.status_code == 200:
                latest_release = release_response.json()
                repo_data['latest_release'] = latest_release
        except:
            repo_data['latest_release'] = None
        
        # Get issue count for personal repos
        if repo_data.get('has_issues', False):
            issues_url = f'https://api.github.com/repos/{repo_name}/issues?state=open'
            try:
                issues_response = requests.get(issues_url, headers=headers)
                if issues_response.status_code == 200:
                    repo_data['open_issues_count'] = len(issues_response.json())
            except:
                repo_data['open_issues_count'] = 0
        
        return repo_data
    except Exception as e:
        print(f"Error fetching data for {repo_name}: {e}")
        return {
            'name': repo_name.split('/')[-1],
            'full_name': repo_name,
            'description': 'Repository information unavailable',
            'html_url': f'https://github.com/{repo_name}',
            'stargazers_count': 0,
            'updated_at': datetime.now().isoformat(),
            'latest_release': None,
            'open_issues_count': 0
        }

def generate_badges(repo_data: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Generate badge HTML for repository."""
    badges = []
    badge_config = config.get('badges', {})
    repo_name = repo_data['full_name']
    
    if badge_config.get('license') and repo_data.get('license'):
        license_name = repo_data['license']['name'].replace(' ', '_')
        badges.append(f'![License](https://img.shields.io/badge/license-{license_name}-blue.svg)')
    
    if badge_config.get('version') and repo_data.get('latest_release'):
        version = repo_data['latest_release']['tag_name']
        badges.append(f'![Version](https://img.shields.io/badge/version-{version}-green.svg)')
    
    if badge_config.get('stars'):
        stars = repo_data.get('stargazers_count', 0)
        badges.append(f'![Stars](https://img.shields.io/github/stars/{repo_name}.svg?style=social)')
    
    if badge_config.get('last_updated'):
        updated = repo_data['updated_at'][:10].replace('-', '_')  # YYYY_MM_DD format
        badges.append(f'![Updated](https://img.shields.io/badge/updated-{updated}-lightgrey.svg)')
    
    if badge_config.get('issue_count') and 'open_issues_count' in repo_data:
        issues = repo_data['open_issues_count']
        color = 'red' if issues > 10 else 'yellow' if issues > 5 else 'green'
        badges.append(f'![Issues](https://img.shields.io/badge/issues-{issues}-{color}.svg)')
    
    return ' '.join(badges)

def generate_repo_section(repo_data: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Generate markdown section for a single repository."""
    name = repo_data['name']
    description = repo_data.get('description', 'No description available')
    url = repo_data['html_url']
    
    # Create repo entry
    section = f"### [{name}]({url})\n"
    section += f"{description}\n\n"
    
    # Add badges if configured
    badges = generate_badges(repo_data, config)
    if badges:
        section += f"{badges}\n\n"
    
    # Add stats if configured
    if config.get('badges', {}).get('stars'):
        stars = repo_data.get('stargazers_count', 0)
        section += f"⭐ {stars} stars"
        
        if repo_data.get('latest_release'):
            version = repo_data['latest_release']['tag_name']
            section += f" • 📦 Latest: {version}"
        
        section += "\n\n"
    
    return section

def generate_readme(config: Dict[str, Any], github_token: str) -> str:
    """Generate complete README.md content."""
    ecosystem_name = config['name']
    description = config['description']
    template_type = config.get('template', 'ecosystem')

    # Header
    readme = f"# {ecosystem_name}\n\n"

    # Add landing image if configured (optional)
    landing_image = config.get('landing_image')
    if landing_image:
        readme += f"![{ecosystem_name}]({landing_image})\n\n"

    readme += f"{description}\n\n"
    
    # Add links if configured
    links = config.get('links', {})
    if links:
        readme += "## Quick Links\n\n"
        for link_name, link_url in links.items():
            readme += f"- [{link_name}]({link_url})\n"
        readme += "\n"
    
    # Generate sections
    sections = config.get('sections', {})
    for section_name, section_config in sections.items():
        readme += f"## {section_name}\n\n"
        
        if section_config.get('description'):
            readme += f"{section_config['description']}\n\n"
        
        # Process repositories in this section
        repos = section_config.get('repos', [])
        for repo_name in repos:
            print(f"Fetching data for {repo_name}...")
            repo_data = get_repo_data(repo_name, github_token)
            readme += generate_repo_section(repo_data, config)
    
    # Footer
    readme += "---\n\n"
    readme += f"*Generated automatically on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
    
    return readme

def main():
    """Main function to generate README from ecosystem.json."""
    if len(sys.argv) != 2:
        print("Usage: python generate_ecosystem_readme.py <ecosystem.json>")
        sys.exit(1)
    
    ecosystem_file = sys.argv[1]
    
    # Check for GitHub token
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    # Load ecosystem configuration
    try:
        with open(ecosystem_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading {ecosystem_file}: {e}")
        sys.exit(1)
    
    # Generate README
    print(f"Generating README for {config['name']}...")
    readme_content = generate_readme(config, github_token)
    
    # Write README.md
    with open('README.md', 'w') as f:
        f.write(readme_content)
    
    print("README.md generated successfully!")

if __name__ == "__main__":
    main()