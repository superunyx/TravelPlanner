import { test, expect } from "@playwright/test";

test.describe("Travel Planner Happy Path", () => {
  test("allows user to access dashboard, navigate to new trip planner, and fill parameters", async ({ page }) => {
    // Navigate to root
    await page.goto("http://localhost:5173/dashboard");

    // Check header branding
    await expect(page.locator("text=TravelPlanner")).toBeVisible();

    // Navigate to trip builder
    await page.click("text=Plan New Trip");
    await expect(page).toHaveURL(/.*\/trips\/new/);

    // Fill Step 1
    await page.fill('input[placeholder*="Rajasthan Heritage Getaway"]', "Kerala Escape");
    await page.fill('input[placeholder*="Udaipur, India"]', "Munnar, Kerala");
    await page.click("text=Next Step");

    // Verify Step 2
    await expect(page.locator("text=Budget & Travelers")).toBeVisible();
  });
});
