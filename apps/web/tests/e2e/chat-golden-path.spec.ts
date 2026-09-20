import { expect, test } from "@playwright/test";

test("home to chat: ask a question and see a grounded, cited answer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /MediRAG helps you understand/i })).toBeVisible();

  await page.getByRole("link", { name: /ask a health question/i }).click();
  await expect(page).toHaveURL(/\/chat/);

  const input = page.getByPlaceholder(/ask about a health topic/i);
  await input.fill("What is paracetamol used for?");
  await input.press("Enter");

  await expect(page.getByText(/paracetamol/i).first()).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/why am i seeing this answer/i)).toBeVisible();

  await page.getByText(/why am i seeing this answer/i).click();
  await expect(page.getByText(/MediRAG Demo Reference Library/i).first()).toBeVisible();
});
