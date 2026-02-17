// 1. Load country boundary and Hansen data
var countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017');
var India = countries.filter(ee.Filter.eq('country_na', 'India'));

var tree_cover_2024 = ee.Image('UMD/hansen/global_forest_change_2024_v1_12');
var lossYear = tree_cover_2024.select('lossyear');  // 1=2001 … 23=2023
var gain = tree_cover_2024.select('gain');          // static gain (2000–2012)

// 2. Clip and mask lossYear to India
lossYear = lossYear.clip(India).updateMask(lossYear);

// 3. Reclassify lossyear into 5‑year periods
var lossPeriod = ee.Image(0).where(lossYear.gte(1).and(lossYear.lte(5)), 1)   // 2001–2005
                           .where(lossYear.gte(6).and(lossYear.lte(10)), 2)  // 2006–2010
                           .where(lossYear.gte(11).and(lossYear.lte(15)), 3) // 2011–2015
                           .where(lossYear.gte(16).and(lossYear.lte(20)), 4) // 2016–2020
                           .where(lossYear.gte(21).and(lossYear.lte(23)), 5) // 2021–2023
                           .rename('lossPeriod')
                           .clip(India)
                           .updateMask(lossYear);

// 4. Add static layers: gain and India boundary
Map.addLayer(gain.clip(India).updateMask(gain), {palette: ['blue']}, 'Forest Gain');
Map.addLayer(ee.Image().paint(India, 0, 1), {palette: ['black']}, 'India Boundary');

// 5. Create and add SEPARATE layers for each 5‑year period (toggleable)
//    Each layer shows only loss pixels from that period, in its own colour.

// Period 1: 2001–2005 (red)
Map.addLayer(
  lossPeriod.eq(1).clip(India).updateMask(lossPeriod.eq(1)),
  {palette: ['red']},
  'Forest Loss 2001–2005',
  true   // layer visible by default
);

// Period 2: 2006–2010 (orange)
Map.addLayer(
  lossPeriod.eq(2).clip(India).updateMask(lossPeriod.eq(2)),
  {palette: ['orange']},
  'Forest Loss 2006–2010',
  true
);

// Period 3: 2011–2015 (yellow)
Map.addLayer(
  lossPeriod.eq(3).clip(India).updateMask(lossPeriod.eq(3)),
  {palette: ['yellow']},
  'Forest Loss 2011–2015',
  true
);

// Period 4: 2016–2020 (green)
Map.addLayer(
  lossPeriod.eq(4).clip(India).updateMask(lossPeriod.eq(4)),
  {palette: ['green']},
  'Forest Loss 2016–2020',
  true
);

// Period 5: 2021–2023 (purple)
Map.addLayer(
  lossPeriod.eq(5).clip(India).updateMask(lossPeriod.eq(5)),
  {palette: ['purple']},
  'Forest Loss 2021–2023',
  true
);



// 6. Create a legend panel (colours exactly as above)
var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px',
    backgroundColor: 'white',
    border: '1px solid black'
  }
});

// Add a title to the legend
legend.add(ui.Label({
  value: 'Forest Loss by Period',
  style: {fontWeight: 'bold', fontSize: '14px', margin: '0 0 4px 0'}
}));

// Define the periods and their colours (keep the same)
var periods = [
  {label: '2001 – 2005', color: 'red'},
  {label: '2006 – 2010', color: 'orange'},
  {label: '2011 – 2015', color: 'yellow'},
  {label: '2016 – 2020', color: 'green'},
  {label: '2021 – 2023', color: 'purple'}
];

// Add a row for each period
periods.forEach(function(period) {
  var row = ui.Panel({
    layout: ui.Panel.Layout.flow('horizontal'),
    style: {margin: '0 0 2px 0'}
  });
  
  // Coloured square
  var colorBox = ui.Label({
    style: {
      backgroundColor: period.color,
      padding: '8px',
      margin: '0 8px 0 0',
      border: '1px solid black'
    }
  });
  
  // Text label
  var description = ui.Label({
    value: period.label,
    style: {margin: '0 0 0 0'}
  });
  
  row.add(colorBox);
  row.add(description);
  legend.add(row);
});

// 7. Add legend to the map
Map.add(legend);

// 8. Center the map
Map.centerObject(India, 4);
