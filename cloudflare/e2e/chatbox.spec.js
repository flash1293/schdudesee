/**
 * E2E tests for the chatbox and search functionality.
 *
 * Requires the test server running (started automatically by Playwright webServer config).
 */

import { test, expect } from '@playwright/test';

// ── Helpers ──────────────────────────────────────────────────────────

function getChatPanel(page) {
  return page.locator('#chat-panel');
}

function getChatMessages(page) {
  return page.locator('#chat-messages');
}

function getChatInput(page) {
  return page.locator('#chat-input');
}

function getChatSend(page) {
  return page.locator('#chat-send');
}

function getChatButton(page) {
  return page.locator('button.chat-btn');
}

function getSearchInput(page) {
  return page.locator('#search');
}

// ── Tests ────────────────────────────────────────────────────────────

test.describe('Chatbox', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('chat button opens and closes the chat panel', async ({ page }) => {
    const panel = getChatPanel(page);
    const chatBtn = getChatButton(page);

    // Initially hidden
    await expect(panel).not.toBeVisible();

    // Click to open
    await chatBtn.click();
    await expect(panel).toBeVisible();

    // Click close button inside panel
    await page.locator('button.chat-close').click();
    await expect(panel).not.toBeVisible();
  });

  test('chat panel opens with welcome message', async ({ page }) => {
    await getChatButton(page).click();
    await expect(getChatPanel(page)).toBeVisible();

    const messages = getChatMessages(page);
    await expect(messages.locator('.chat-msg.assistant')).toHaveCount(1);
    await expect(messages.locator('.chat-msg.assistant')).toContainText(
      /Hallo.*KI-Assistent/i
    );
  });

  test('typing a message and sending shows a response', async ({ page }) => {
    await getChatButton(page).click();
    await expect(getChatPanel(page)).toBeVisible();

    const input = getChatInput(page);
    await input.fill('Was ist heute los?');

    await getChatSend(page).click();

    // Wait for the API response (mock LLM is synchronous, so fast)
    await page.waitForTimeout(500);

    // Should have user message + assistant response (plus initial welcome = 3)
    const messages = getChatMessages(page);
    await expect(messages.locator('.chat-msg')).toHaveCount(3);

    // The last message should be from assistant with content
    const lastMsg = messages.locator('.chat-msg').last();
    await expect(lastMsg).toHaveClass(/assistant/);
    await expect(lastMsg).not.toBeEmpty();
  });

  test('send button is disabled while waiting for response', async ({ page }) => {
    await getChatButton(page).click();
    const input = getChatInput(page);
    const sendBtn = getChatSend(page);

    // Fill input first
    await input.fill('Was ist heute los?');

    // Check disabled state DURING the sendChat execution (before await)
    const disabledDuringCall = await page.evaluate(() => {
      const sendBtn = document.getElementById('chat-send');
      const input = document.getElementById('chat-input');
      input.value = 'Test';
      // Call sendChat but capture state before any await
      const promise = window.sendChat();
      const isDisabled = sendBtn.disabled;
      return { isDisabled, inputCleared: input.value === '' };
    });

    expect(disabledDuringCall.isDisabled).toBe(true);
    expect(disabledDuringCall.inputCleared).toBe(true);

    // Wait for the response to complete
    await page.waitForTimeout(500);

    // Button should be re-enabled after response
    await expect(sendBtn).toBeEnabled();
  });

  test('sending an empty message does nothing', async ({ page }) => {
    await getChatButton(page).click();
    const sendBtn = getChatSend(page);

    // Count messages before
    const initialCount = await getChatMessages(page).locator('.chat-msg').count();

    // Click send with empty input
    await sendBtn.click();
    await page.waitForTimeout(200);

    // No new messages should appear
    await expect(getChatMessages(page).locator('.chat-msg')).toHaveCount(initialCount);
  });

  test('chat input can be submitted via Enter key', async ({ page }) => {
    await getChatButton(page).click();
    const input = getChatInput(page);

    await input.fill('Events am Wochenende');
    await input.press('Enter');

    await page.waitForTimeout(500);

    const messages = getChatMessages(page);
    await expect(messages.locator('.chat-msg')).toHaveCount(3);
  });
});

test.describe('Search', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('search input is visible and functional', async ({ page }) => {
    const search = getSearchInput(page);
    await expect(search).toBeVisible();
    await expect(search).toHaveAttribute('placeholder', 'Suchen…');
  });

  test('typing a search term filters events', async ({ page }) => {
    const search = getSearchInput(page);

    // Search for "Fußball" — this matches a future event (June 11)
    await search.fill('Fußball');

    // Wait for debounce (300ms) + API response
    await page.waitForTimeout(1000);

    // Should show matching events
    const events = page.locator('#events .event');
    await expect(events).toHaveCount(1);
    await expect(events.locator('text=Fußball')).toHaveCount(1);
  });

  test('clearing search shows all upcoming events', async ({ page }) => {
    const search = getSearchInput(page);

    // Search for something specific
    await search.fill('Museum');
    await page.waitForTimeout(1000);

    // Now clear
    await search.fill('');
    await page.waitForTimeout(1000);

    // Should show multiple events (all upcoming)
    const events = page.locator('#events .event');
    const count = await events.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('search with no results shows empty state', async ({ page }) => {
    const search = getSearchInput(page);

    await search.fill('xyznonexistent12345');
    await page.waitForTimeout(1000);

    // Should show no events
    const events = page.locator('#events .event');
    await expect(events).toHaveCount(0);
  });
});

test.describe('SSR Initial Load', () => {

  test('page loads and renders upcoming events', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // Should have event cards rendered
    const events = page.locator('#events .event');
    await expect(events).not.toHaveCount(0);

    // Should show upcoming events (June+)
    // "Hope is a dangerous thing" is on June 15 — should be visible
    await expect(page.locator('text=Hope is a dangerous thing')).toBeVisible();
  });

  test('page title is set correctly', async ({ page }) => {
    await page.goto('/');

    // Check page title
    await expect(page).toHaveTitle(/Was geht, Stutensee/);

    // Check meta description
    const metaDesc = page.locator('meta[name="description"]');
    await expect(metaDesc).toHaveAttribute('content', /Alle Veranstaltungen in Stutensee/);
  });

  test('event detail page renders correctly', async ({ page }) => {
    // Navigate to an event detail page
    await page.goto('/events/1/10-jahre-red-horse-festival');
    await page.waitForLoadState('networkidle');

    // Should show event title (second h1)
    const heading = page.locator('h1').last();
    await expect(heading).toContainText('Red Horse Festival');

    // Should show a back link
    await expect(page.locator('text=Zurück zur Übersicht')).toBeVisible();

    // Should have event metadata (organizer tag)
    await expect(page.locator('.tag-organizer')).toContainText('Jugendzentrum GrauBau');
  });
});
