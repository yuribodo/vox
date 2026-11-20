import { expect, test } from "@playwright/test";

const origin = "http://127.0.0.1:4173";
const commands = [
  "git clone https://github.com/yuribodo/vox.git && cd vox",
  "make build && make fetch-whisper && make doctor",
  "make desktop-shortcut",
];

test("static /vox landing fits and copies each command", async ({ page, context }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("requestfailed", (request) => errors.push(`Failed request: ${request.url()}`));
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
  });
  // Never contact live services, follow GitHub links, or run copied commands.
  await context.route("**/*", async (route) => {
    if (new URL(route.request().url()).origin === origin) await route.continue();
    else {
      errors.push(`Blocked external request: ${route.request().url()}`);
      await route.abort();
    }
  });
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin });
  const response = await page.goto("/vox/");
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("main")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const noOverflow = async () => {
    expect(await page.evaluate(() => Math.max(
      document.documentElement.scrollWidth, document.body.scrollWidth,
    ) - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  };
  await noOverflow();
  await expect(page.getByRole("button", { name: /^Copy command:/ })).toHaveCount(3);
  for (const command of commands) {
    const button = page.getByRole("button", { name: `Copy command: ${command}`, exact: true });
    await button.scrollIntoViewIfNeeded();
    await expect(button).toBeInViewport();
    // Repeat after the feedback resets; verify real clipboard contents each time.
    for (let attempt = 0; attempt < 2; attempt++) {
      await page.evaluate(() => navigator.clipboard.writeText("smoke sentinel"));
      await button.click();
      await expect(button).toHaveText("copied");
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(command);
      await expect(button).toHaveText("copy");
    }
    await noOverflow();
  }
  expect(errors, "browser errors or unexpected network requests").toEqual([]);
});
