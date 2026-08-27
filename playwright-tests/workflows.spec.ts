import { test, expect } from '@playwright/test';

test('catalog tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Species catalog' }).click();

  await expect(
    page.getByText('Search common or scientific name')
  ).toBeVisible();
});

test('record sighting tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Record sighting' }).click();

  await expect(
    page.getByRole('combobox', { name: 'Species' }).first()
  ).toBeVisible();
});

test('my sightings tutorial', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'My sightings' }).click();

  await expect(
    page.getByRole('link', { name: 'My sightings' })
  ).toBeVisible();
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
