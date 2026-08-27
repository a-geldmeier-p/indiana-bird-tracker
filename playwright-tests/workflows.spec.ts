import { test, expect } from '@playwright/test';

test('catalog tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Species catalog' }).click();

  await page.getByLabel('Search common or scientific name').fill('cardinal');
  await page.getByRole('button', { name: 'Filter catalog' }).click();
  await expect(
    page.getByText('Search common or scientific name')
  ).toBeVisible();
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
  await page.getByLabel('Location').fill('Eagle Creek Park');
  await page.getByLabel('Indiana county').fill('Marion');
  await page.getByLabel('Notes (optional)').fill('Playwright tutorial sighting');
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
  await page.getByRole('button', { name: 'Filter sightings' }).click();
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
