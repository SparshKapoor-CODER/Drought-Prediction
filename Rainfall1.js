// ==============================
// 1. Load India boundary
// ==============================
var countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017');
var India = countries.filter(ee.Filter.eq('country_na', 'India'));

// ==============================
// 2. Load CHIRPS Daily Rainfall
// ==============================
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
                .filterDate('2001-01-01', '2023-12-31')
                .filterBounds(India)
                .select('precipitation');

// ==============================
// 3. Define 5‑year periods (same as forest loss)
// ==============================
var periods = [
  {name: '2001–2005', start: '2001-01-01', end: '2005-12-31', color: 'blue'},
  {name: '2006–2010', start: '2006-01-01', end: '2010-12-31', color: 'cyan'},
  {name: '2011–2015', start: '2011-01-01', end: '2015-12-31', color: 'green'},
  {name: '2016–2020', start: '2016-01-01', end: '2020-12-31', color: 'lime'},
  {name: '2021–2023', start: '2021-01-01', end: '2023-12-31', color: 'purple'}
];

// ==============================
// 4. Visualization settings (common scale)
// ==============================
var rainVis = {
  min: 0,
  max: 15000,          // total mm over 5 years (adjust if needed)
  palette: ['white', 'blue', 'cyan', 'green', 'yellow', 'red']
};

// ==============================
// 5. Add each period as a separate layer
// ==============================
periods.forEach(function(p) {
  var periodRain = chirps
                    .filterDate(p.start, p.end)
                    .sum()
                    .clip(India);
  
  Map.addLayer(
    periodRain,
    rainVis,
    'Rainfall ' + p.name,
    false   // start hidden
  );
});

// ==============================
// 6. (Optional) Mean annual rainfall layer
// ==============================
var meanAnnual = chirps
                  .filterDate('2001-01-01', '2023-12-31')
                  .mean()
                  .multiply(365)
                  .clip(India);

Map.addLayer(
  meanAnnual,
  {min: 0, max: 3000, palette: ['white', 'blue', 'green', 'yellow', 'red']},
  'Mean Annual Rainfall (2001–2023)',
  true
);

// ==============================
// 7. Add India boundary
// ==============================
Map.addLayer(ee.Image().paint(India, 0, 1), {palette: ['black']}, 'India Boundary');

// ==============================
// 8. Center map
// ==============================
Map.centerObject(India, 4);

// ==============================
// 9. Add a legend for rainfall
// ==============================
var rainfallLegend = ui.Panel({
  style: {
    position: 'bottom-right',
    padding: '8px 15px',
    backgroundColor: 'white',
    border: '1px solid black'
  }
});

// Title
rainfallLegend.add(ui.Label({
  value: 'Rainfall (mm / 5‑year period)',
  style: {fontWeight: 'bold', fontSize: '14px', margin: '0 0 4px 0'}
}));

// Create a horizontal row of colour boxes
var colorRow = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: {margin: '0 0 4px 0'}   // removed invalid 'stretch'
});

// Add a coloured box for each palette colour
rainVis.palette.forEach(function(hex) {
  var colorBox = ui.Label({
    style: {
      backgroundColor: hex,
      padding: '8px',
      margin: '0 2px 0 0',
      border: '1px solid black'
      // removed invalid 'stretch'
    }
  });
  colorRow.add(colorBox);
});

rainfallLegend.add(colorRow);

var minMaxPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: {margin: '0 0 2px 0'}
});

minMaxPanel.add(ui.Label('0'));
minMaxPanel.add(ui.Label(rainVis.max + '+'));

rainfallLegend.add(minMaxPanel);

// Add the legend to the map
Map.add(rainfallLegend);