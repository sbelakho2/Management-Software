#!/usr/bin/env python3
"""
Comprehensive Role-based UI Audit with Screenshots

This script logs in as each user role, captures screenshots of all pages,
and analyzes them for errors.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

# Configuration
BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
SCREENSHOT_DIR = Path(__file__).parent.parent / "role-screenshots"
PASSWORD = "TestPassword123!"
EMAIL_DOMAIN = "senseitest.com"

# All user roles with their expected sidebar features
ROLES_AND_FEATURES = {
    "admin": ["today", "tasks", "executive", "analytics", "pipeline", "rfqs", "quotes", "customers", "production", "projects", "products", "obeya", "a3", "ctq", "exceptions", "quality", "andon", "maintenance", "supply-chain", "warehouse", "training", "finance", "hr", "it", "settings", "admin"],
    "ceo": ["today", "tasks", "executive", "analytics", "finance", "hr"],
    "gm": ["today", "tasks", "executive", "analytics", "production", "projects", "quality", "maintenance", "warehouse", "finance", "hr"],
    "sales": ["today", "tasks", "pipeline", "rfqs", "quotes", "customers", "products"],
    "sales_engineer": ["today", "tasks", "pipeline", "rfqs", "quotes", "customers", "products"],
    "quality": ["today", "tasks", "production", "quality", "a3", "ctq", "exceptions"],
    "supervisor": ["today", "tasks", "production", "projects", "quality", "andon", "maintenance"],
    "operator": ["today", "tasks", "production", "andon"],
    "finance": ["today", "tasks", "finance", "analytics"],
    "hr": ["today", "tasks", "hr", "training"],
    "it": ["today", "tasks", "it", "settings"],
    "warehouse": ["today", "tasks", "warehouse", "supply-chain"],
    "auditor": ["today", "analytics", "finance", "quality"],
    "supply_chain": ["today", "tasks", "supply-chain", "warehouse", "products"],
    "team_lead": ["today", "tasks", "production", "projects", "quality", "andon"],
}

# All pages to test
ALL_PAGES = [
    "/today",
    "/tasks",
    "/executive",
    "/analytics",
    "/pipeline",
    "/rfqs",
    "/quotes",
    "/customers",
    "/production",
    "/projects",
    "/products",
    "/obeya",
    "/a3",
    "/ctq",
    "/exceptions",
    "/quality",
    "/andon",
    "/maintenance",
    "/supply-chain",
    "/warehouse",
    "/training",
    "/finance",
    "/hr",
    "/it",
    "/settings",
    "/admin",
]

class RoleAudit:
    def __init__(self):
        self.results = {}
        self.errors = []
        
    async def login(self, page: Page, role: str) -> bool:
        """Login as a specific role."""
        email = f"{role}@{EMAIL_DOMAIN}"
        
        try:
            await page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
            
            # Fill login form
            await page.fill('input[name="email"], input[type="email"]', email)
            await page.fill('input[name="password"], input[type="password"]', PASSWORD)
            
            # Submit
            await page.click('button[type="submit"]')
            
            # Wait for redirect away from login
            try:
                await page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
                print(f"  ✓ Logged in as {role}")
                return True
            except:
                print(f"  ✗ Login failed for {role}")
                return False
                
        except Exception as e:
            print(f"  ✗ Login error for {role}: {e}")
            return False
    
    async def capture_page(self, page: Page, role: str, page_path: str, index: int) -> dict:
        """Capture a screenshot of a page and check for errors."""
        role_dir = SCREENSHOT_DIR / role
        role_dir.mkdir(parents=True, exist_ok=True)
        
        page_name = page_path.strip("/").replace("/", "-") or "home"
        screenshot_path = role_dir / f"{index:02d}-{page_name}.png"
        
        result = {
            "path": page_path,
            "screenshot": str(screenshot_path),
            "accessible": False,
            "errors": [],
            "warnings": [],
        }
        
        try:
            response = await page.goto(f"{BASE_URL}{page_path}", wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(1000)  # Wait for animations
            
            # Check if redirected to login (unauthorized)
            if "/login" in page.url:
                result["accessible"] = False
                result["warnings"].append("Redirected to login - unauthorized")
            else:
                result["accessible"] = True
                
                # Check for error indicators in the page
                content = await page.content()
                
                # Check for common error patterns
                error_patterns = [
                    (r"500\s*-?\s*(Internal Server Error|Server Error)", "500 Internal Server Error"),
                    (r"404\s*-?\s*(Not Found|Page not found)", "404 Not Found"),
                    (r"403\s*-?\s*(Forbidden|Access Denied)", "403 Forbidden"),
                    (r"401\s*-?\s*(Unauthorized)", "401 Unauthorized"),
                    (r"Error:\s*(.{10,100})", "Error message found"),
                    (r"Something went wrong", "Something went wrong"),
                    (r"Failed to (load|fetch)", "Failed to load/fetch"),
                    (r"Cannot read propert", "JavaScript error"),
                    (r"undefined is not", "JavaScript error"),
                    (r"null is not", "JavaScript error"),
                ]
                
                for pattern, error_type in error_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        result["errors"].append(error_type)
                
                # Check for console errors
                # (Already captured via page error event)
                
            # Take screenshot
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
        except Exception as e:
            result["errors"].append(f"Page load error: {str(e)[:100]}")
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except:
                pass
        
        return result
    
    async def capture_sidebar(self, page: Page, role: str) -> list:
        """Capture sidebar links."""
        sidebar_links = []
        
        try:
            # Find sidebar navigation links
            links = await page.query_selector_all('nav a, aside a, [data-testid="sidebar"] a')
            
            for link in links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and text:
                    sidebar_links.append({"href": href, "text": text.strip()})
            
            # Take sidebar screenshot
            role_dir = SCREENSHOT_DIR / role
            sidebar_screenshot = role_dir / "00-sidebar.png"
            
            sidebar = await page.query_selector('aside, nav[role="navigation"], [data-testid="sidebar"]')
            if sidebar:
                await sidebar.screenshot(path=str(sidebar_screenshot))
            else:
                await page.screenshot(path=str(sidebar_screenshot), full_page=True)
                
        except Exception as e:
            print(f"  ! Sidebar capture error: {e}")
        
        return sidebar_links
    
    async def audit_role(self, browser: Browser, role: str) -> dict:
        """Audit a single role."""
        print(f"\n🔍 Auditing role: {role}")
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))
        
        role_result = {
            "role": role,
            "login_success": False,
            "sidebar_links": [],
            "pages": [],
            "console_errors": console_errors,
            "summary": {
                "total_pages": len(ALL_PAGES),
                "accessible_pages": 0,
                "pages_with_errors": 0,
                "unauthorized_pages": 0,
            }
        }
        
        # Login
        if not await self.login(page, role):
            role_result["login_success"] = False
            await context.close()
            return role_result
        
        role_result["login_success"] = True
        
        # Capture sidebar
        role_result["sidebar_links"] = await self.capture_sidebar(page, role)
        
        # Visit each page
        for i, page_path in enumerate(ALL_PAGES):
            result = await self.capture_page(page, role, page_path, i + 1)
            role_result["pages"].append(result)
            
            if result["accessible"]:
                role_result["summary"]["accessible_pages"] += 1
            else:
                role_result["summary"]["unauthorized_pages"] += 1
            
            if result["errors"]:
                role_result["summary"]["pages_with_errors"] += 1
                
            # Status indicator
            status = "✓" if result["accessible"] and not result["errors"] else ("⚠" if result["accessible"] else "✗")
            errors = f" [{', '.join(result['errors'][:2])}]" if result["errors"] else ""
            print(f"  {status} {page_path}{errors}")
        
        # Add console errors to result
        role_result["console_errors"] = console_errors[:50]  # Limit to 50
        
        await context.close()
        return role_result
    
    async def run_audit(self):
        """Run full audit for all roles."""
        print("=" * 60)
        print("COMPREHENSIVE ROLE-BASED UI AUDIT")
        print("=" * 60)
        
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for role in ROLES_AND_FEATURES.keys():
                result = await self.audit_role(browser, role)
                self.results[role] = result
            
            await browser.close()
        
        # Save results
        results_file = SCREENSHOT_DIR / "audit-results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Generate summary report
        self.generate_report()
        
    def generate_report(self):
        """Generate a summary report."""
        print("\n" + "=" * 60)
        print("AUDIT SUMMARY REPORT")
        print("=" * 60)
        
        all_errors = []
        
        for role, result in self.results.items():
            print(f"\n📊 {role.upper()}")
            print(f"   Login: {'✓' if result['login_success'] else '✗'}")
            print(f"   Accessible Pages: {result['summary']['accessible_pages']}/{result['summary']['total_pages']}")
            print(f"   Pages with Errors: {result['summary']['pages_with_errors']}")
            print(f"   Sidebar Links: {len(result['sidebar_links'])}")
            
            # Collect errors
            for page_result in result["pages"]:
                if page_result["errors"]:
                    for error in page_result["errors"]:
                        all_errors.append({
                            "role": role,
                            "page": page_result["path"],
                            "error": error,
                            "screenshot": page_result["screenshot"],
                        })
        
        # Print all errors
        if all_errors:
            print("\n" + "=" * 60)
            print("ERRORS FOUND")
            print("=" * 60)
            for err in all_errors:
                print(f"\n❌ {err['role']} - {err['page']}")
                print(f"   Error: {err['error']}")
                print(f"   Screenshot: {err['screenshot']}")
        else:
            print("\n✅ No page errors found!")
        
        # Save error summary
        errors_file = SCREENSHOT_DIR / "errors-summary.json"
        with open(errors_file, "w") as f:
            json.dump(all_errors, f, indent=2)
        
        print(f"\n📁 Screenshots saved to: {SCREENSHOT_DIR}")
        print(f"📄 Full results: {SCREENSHOT_DIR}/audit-results.json")
        print(f"📄 Errors summary: {SCREENSHOT_DIR}/errors-summary.json")


if __name__ == "__main__":
    audit = RoleAudit()
    asyncio.run(audit.run_audit())
