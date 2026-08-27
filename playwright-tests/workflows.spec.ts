import { test, expect } from '@playwright/test';

test('catalog tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Species catalog' }).click();

  await page.getByLabel('Search common or scientific name').fill('cardinal');
  await page.locator('#species-bird_group-selectized').click();
  await page.locator('.selectize-dropdown:visible .option').nth(1).click();
  await page.locator('#species-status_note-selectized').click();
  await page.locator('.selectize-dropdown:visible .option').nth(1).click();
  await page.getByRole('button', { name: 'Filter catalog' }).click();
  await expect(
    page.getByText('Search common or scientific name')
  ).toBeVisible();
  await page.mouse.wheel(0, 900);
  await page.getByRole('button', { name: 'Reset filters' }).click();
});

test('record sighting tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Record sighting' }).click();

  const species = page.locator('#record-species_code-selectized');
  await species.click();
  await page.locator('.selectize-dropdown .option').first().waitFor();
  await page.locator('.selectize-dropdown .option').first().click();
  await page.getByLabel('Observation time').fill('12:00');
  await page.locator('#record-observation_date').fill('2026-08-20');
  await page.getByLabel('Location').fill('Eagle Creek Park');
  await page.getByLabel('Indiana county').fill('Marion');
  await page.getByLabel('Notes (optional)').fill('Playwright tutorial sighting');
  await page.getByLabel('Or photo path or URL (optional)').fill('https://example.com/indiana-bird.jpg');
  await page.getByRole('button', { name: 'Save sighting' }).click();
  await expect(page.getByRole('status')).toContainText('Saved sighting');
});

test('my sightings tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'My sightings' }).click();

  await expect(
    page.getByRole('heading', { name: 'Filter my sightings' })
  ).toBeVisible();
  await page.getByLabel('Filter by observation date').check();
  const dateRange = page.locator('#sightings-date_range input');
  await dateRange.first().fill('2026-08-01');
  await dateRange.last().fill('2026-08-26');
  await page.getByRole('button', { name: 'Filter sightings' }).click();
  await page.mouse.wheel(0, 1200);
  await expect(page.getByRole('heading', { name: 'Sighting photos' })).toBeVisible();
  await page.getByRole('button', { name: 'Reset filters' }).click();
});

test('dashboard tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Dashboard' }).click();

  await expect(
    page.getByText('Total sightings')
  ).toBeVisible();

  await expect(
    page.getByText('Distinct species')
  ).toBeVisible();
});
