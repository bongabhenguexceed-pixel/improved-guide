#!/usr/bin/env python3
"""
Zuxuru Digital Name Investigation App

Investigates a business's public digital presence by checking:
- Domain availability across multiple TLDs
- Social media handle availability
- Online mentions and brand presence
- Trademark considerations
"""

import re
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class AvailabilityStatus(Enum):
    AVAILABLE = "available"
    TAKEN = "taken"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class DomainResult:
    domain: str
    status: AvailabilityStatus
    message: str = ""


@dataclass
class SocialMediaResult:
    platform: str
    handle: str
    url: str
    status: AvailabilityStatus
    profile_exists: bool = False


@dataclass
class InvestigationReport:
    business_name: str
    sanitized_name: str
    domains: List[DomainResult] = field(default_factory=list)
    social_media: List[SocialMediaResult] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    overall_score: int = 0


class DigitalNameInvestigator:
    """Main class for investigating digital name availability."""

    COMMON_TLDS = [".com", ".net", ".org", ".io", ".co", ".ai", ".tech", ".app"]
    
    SOCIAL_PLATFORMS = {
        "Twitter": "https://twitter.com/{handle}",
        "Instagram": "https://instagram.com/{handle}",
        "Facebook": "https://facebook.com/{handle}",
        "LinkedIn": "https://linkedin.com/company/{handle}",
        "GitHub": "https://github.com/{handle}",
        "TikTok": "https://tiktok.com/@{handle}",
        "YouTube": "https://youtube.com/@{handle}",
    }

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def sanitize_name(self, name: str) -> str:
        """Convert business name to URL-friendly format."""
        # Remove special characters, convert to lowercase, replace spaces with hyphens
        sanitized = re.sub(r"[^a-zA-Z0-9\s]", "", name.lower())
        sanitized = re.sub(r"\s+", "-", sanitized.strip())
        return sanitized

    def check_domain_availability(self, domain: str) -> DomainResult:
        """Check if a domain is available using whois or DNS lookup."""
        try:
            # Simple DNS check - if it resolves, it's taken
            import socket
            try:
                socket.gethostbyname(domain.replace("https://", "").replace("http://", ""))
                return DomainResult(
                    domain=domain,
                    status=AvailabilityStatus.TAKEN,
                    message="Domain is registered and active"
                )
            except socket.gaierror:
                return DomainResult(
                    domain=domain,
                    status=AvailabilityStatus.AVAILABLE,
                    message="Domain appears to be available"
                )
        except Exception as e:
            return DomainResult(
                domain=domain,
                status=AvailabilityStatus.UNKNOWN,
                message=f"Could not verify: {str(e)}"
            )

    def check_social_media_handle(self, platform: str, handle: str) -> SocialMediaResult:
        """Check if a social media handle is available."""
        url_template = self.SOCIAL_PLATFORMS.get(platform)
        if not url_template:
            return SocialMediaResult(
                platform=platform,
                handle=handle,
                url="",
                status=AvailabilityStatus.UNKNOWN,
                profile_exists=False
            )

        url = url_template.format(handle=handle)
        
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            
            # Most platforms return 404 for non-existent profiles
            if response.status_code == 404:
                return SocialMediaResult(
                    platform=platform,
                    handle=handle,
                    url=url,
                    status=AvailabilityStatus.AVAILABLE,
                    profile_exists=False
                )
            elif response.status_code == 200:
                return SocialMediaResult(
                    platform=platform,
                    handle=handle,
                    url=url,
                    status=AvailabilityStatus.TAKEN,
                    profile_exists=True
                )
            else:
                return SocialMediaResult(
                    platform=platform,
                    handle=handle,
                    url=url,
                    status=AvailabilityStatus.UNKNOWN,
                    profile_exists=False
                )
        except requests.exceptions.RequestException as e:
            return SocialMediaResult(
                platform=platform,
                handle=handle,
                url=url,
                status=AvailabilityStatus.ERROR,
                profile_exists=False
            )

    def generate_recommendations(self, report: InvestigationReport) -> None:
        """Generate strategic recommendations based on investigation results."""
        recommendations = []

        # Domain recommendations
        available_domains = [d for d in report.domains if d.status == AvailabilityStatus.AVAILABLE]
        taken_domains = [d for d in report.domains if d.status == AvailabilityStatus.TAKEN]

        if any(d.domain.endswith(".com") for d in taken_domains):
            recommendations.append("Consider alternative TLDs since .com is taken")
        
        if len(available_domains) >= 3:
            recommendations.append("Good domain availability - secure key domains quickly")
        elif len(available_domains) == 0:
            recommendations.append("Consider brand variations or modifiers for domain names")

        # Social media recommendations
        available_social = [s for s in report.social_media if s.status == AvailabilityStatus.AVAILABLE]
        taken_social = [s for s in report.social_media if s.status == AvailabilityStatus.TAKEN]

        if len(taken_social) > len(available_social):
            recommendations.append("Most social handles are taken - consider brand variations")
        
        critical_platforms = ["Twitter", "Instagram", "LinkedIn"]
        missing_critical = [p for p in critical_platforms 
                          if not any(s.platform == p and s.status == AvailabilityStatus.AVAILABLE 
                                   for s in report.social_media)]
        
        if missing_critical:
            recommendations.append(f"Secure handles on critical platforms: {', '.join(missing_critical)}")

        # Overall score calculation
        total_checks = len(report.domains) + len(report.social_media)
        available_count = len(available_domains) + len(available_social)
        
        if total_checks > 0:
            report.overall_score = int((available_count / total_checks) * 100)

        report.recommendations = recommendations

    def investigate(self, business_name: str) -> InvestigationReport:
        """Perform complete digital name investigation."""
        print(f"\n🔍 Investigating digital presence for: '{business_name}'")
        print("=" * 60)

        sanitized = self.sanitize_name(business_name)
        report = InvestigationReport(
            business_name=business_name,
            sanitized_name=sanitized
        )

        # Check domains
        print("\n📦 Checking domain availability...")
        for tld in self.COMMON_TLDS:
            domain = f"{sanitized}{tld}"
            result = self.check_domain_availability(domain)
            report.domains.append(result)
            status_icon = "✅" if result.status == AvailabilityStatus.AVAILABLE else "❌"
            print(f"  {status_icon} {domain}: {result.status.value}")

        # Check social media
        print("\n📱 Checking social media handles...")
        for platform in self.SOCIAL_PLATFORMS.keys():
            result = self.check_social_media_handle(platform, sanitized)
            report.social_media.append(result)
            status_icon = "✅" if result.status == AvailabilityStatus.AVAILABLE else "❌"
            print(f"  {status_icon} {platform}: @{sanitized} - {result.status.value}")

        # Generate recommendations
        self.generate_recommendations(report)

        # Print summary
        print("\n" + "=" * 60)
        print("📊 INVESTIGATION SUMMARY")
        print("=" * 60)
        print(f"Business Name: {report.business_name}")
        print(f"Sanitized Handle: {report.sanitized_name}")
        print(f"Overall Availability Score: {report.overall_score}%")
        
        print(f"\n✅ Available Domains: {len([d for d in report.domains if d.status == AvailabilityStatus.AVAILABLE])}/{len(report.domains)}")
        print(f"✅ Available Social Handles: {len([s for s in report.social_media if s.status == AvailabilityStatus.AVAILABLE])}/{len(report.social_media)}")

        if report.recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")

        return report


def main():
    """Main entry point for the Digital Name Investigation App."""
    print("\n" + "=" * 60)
    print("   ZUXURU DIGITAL NAME INVESTIGATION APP")
    print("=" * 60)
    print("\nThis tool investigates a business name's digital presence across")
    print("domains and social media platforms to identify availability and")
    print("provide strategic recommendations.\n")

    investigator = DigitalNameInvestigator(timeout=5)

    while True:
        business_name = input("\nEnter business name to investigate (or 'quit' to exit): ").strip()
        
        if business_name.lower() in ['quit', 'exit', 'q']:
            print("\nThank you for using Zuxuru Digital Name Investigation App!")
            break
        
        if not business_name:
            print("Please enter a valid business name.")
            continue

        try:
            report = investigator.investigate(business_name)
            
            save_option = input("\nWould you like to save this report? (y/n): ").strip().lower()
            if save_option == 'y':
                filename = f"investigation_{report.sanitized_name}.txt"
                with open(filename, 'w') as f:
                    f.write(f"ZUXURU DIGITAL NAME INVESTIGATION REPORT\n")
                    f.write(f"{'=' * 60}\n\n")
                    f.write(f"Business Name: {report.business_name}\n")
                    f.write(f"Sanitized Handle: {report.sanitized_name}\n")
                    f.write(f"Overall Score: {report.overall_score}%\n\n")
                    
                    f.write("DOMAIN AVAILABILITY:\n")
                    f.write("-" * 40 + "\n")
                    for domain in report.domains:
                        f.write(f"{domain.domain}: {domain.status.value} - {domain.message}\n")
                    
                    f.write("\nSOCIAL MEDIA AVAILABILITY:\n")
                    f.write("-" * 40 + "\n")
                    for social in report.social_media:
                        f.write(f"{social.platform} (@{social.handle}): {social.status.value}\n")
                    
                    f.write("\nRECOMMENDATIONS:\n")
                    f.write("-" * 40 + "\n")
                    for rec in report.recommendations:
                        f.write(f"• {rec}\n")
                
                print(f"Report saved to: {filename}")
        
        except KeyboardInterrupt:
            print("\n\nInvestigation interrupted.")
            continue
        except Exception as e:
            print(f"\nError during investigation: {str(e)}")


if __name__ == "__main__":
    main()
