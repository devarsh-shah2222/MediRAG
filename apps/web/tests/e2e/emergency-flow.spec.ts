import { expect, test } from "@playwright/test";

test("emergency-pattern message short-circuits to the emergency navigation state", async ({ page }) => {
  await page.goto("/chat");

  const input = page.getByPlaceholder(/ask about a health topic/i);
  await input.fill("I can't breathe and my lips are turning blue");
  await input.press("Enter");

  await expect(page.getByRole("alert")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/urgent medical attention may be needed/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /call emergency service/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /find nearby hospital/i })).toBeVisible();
});
