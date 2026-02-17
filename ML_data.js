// Create feature image for 2021–2023 (same as in makeTrainingImage but without label)
// ============================================================
// 1. Load boundaries and datasets
// ============================================================
var countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017');
var india = countries.filter(ee.Filter.eq('country_na', 'India'));

// Hansen forest change data
var hansen = ee.Image('UMD/hansen/global_forest_change_2024_v1_12');
var treeCover2000 = hansen.select('treecover2000');   // tree cover % in 2000
var lossYear = hansen.select('lossyear');             // 1=2001 … 23=2023

// CHIRPS daily rainfall
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
                .filterBounds(india)
                .select('precipitation');

// ============================================================
// 2. Helper function: total rainfall for a date range
// ============================================================
function rainfallTotal(start, end) {
  return chirps.filterDate(start, end).sum();
}

// ============================================================
// 3. Define the 5‑year periods (same as before)
// ============================================================
var periodDefs = [
  {name: '2001_2005', start: '2001-01-01', end: '2005-12-31'},
  {name: '2006_2010', start: '2006-01-01', end: '2010-12-31'},
  {name: '2011_2015', start: '2011-01-01', end: '2015-12-31'},
  {name: '2016_2020', start: '2016-01-01', end: '2020-12-31'},
  {name: '2021_2023', start: '2021-01-01', end: '2023-12-31'}
];

// ============================================================
// 4. Compute mean and standard deviation of 5‑year totals
//    (using all five periods)
// ============================================================
var fiveYearTotals = ee.ImageCollection.fromImages(
  periodDefs.map(function(p) {
    return rainfallTotal(p.start, p.end)
            .clip(india)
            .set('period', p.name);
  })
);

var mean5yr = fiveYearTotals.mean();
var std5yr = fiveYearTotals.reduce(ee.Reducer.stdDev());

// ============================================================
// 5. Build the feature image for 2021–2023
// ============================================================
var featPeriod = periodDefs[4];   // 2021-2023

// Total rainfall during the feature period
var rainFeat = rainfallTotal(featPeriod.start, featPeriod.end)
                .rename('rainfall_total');

// Rainfall anomaly (difference from long‑term mean)
var anomaly = rainFeat.subtract(mean5yr).rename('rainfall_anomaly');

// SPI approximation (z‑score)
var spi = rainFeat.subtract(mean5yr).divide(std5yr).rename('spi');

// Tree cover in 2000 (static)
var cover = treeCover2000.rename('treecover2000');

// Past loss: loss that occurred BEFORE 2021
// lossYear values: 1=2001 … 23=2023. So lossYear < 21 means before 2021.
var lossBefore = lossYear.lt(21).rename('past_loss');

// Combine all bands into one image
var features2021_2023 = ee.Image.cat([rainFeat, anomaly, spi, cover, lossBefore])
                         .clip(india)
                         .float();   // convert to float to reduce file size

// ============================================================
// 6. Export the feature image to Google Drive
// ============================================================
Export.image.toDrive({
  image: features2021_2023,
  description: 'features_2021_2023',
  folder: 'GEE_exports',                // change if desired
  fileNamePrefix: 'features_2021_2023',
  region: india.geometry(),
  scale: 1000,                          // 1 km resolution – adjust if needed
  maxPixels: 1e13,
  crs: 'EPSG:4326'                      // WGS84 latitude/longitude
});

// Optional: print something to confirm
print('Export started. Check the Tasks tab.');