// ============================================================
// 1. Load your risk map (update path if necessary)
// ============================================================
var riskImage = ee.Image('users/sparsh312333/forest_loss_risk_2021_2023');

// ============================================================
// 2. Load India boundary for masking and outline
// ============================================================
var countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017');
var india = countries.filter(ee.Filter.eq('country_na', 'India'));

// ============================================================
// 3. (Optional) Load tree cover to mask non‑forest areas
//    This ensures we only show risk where forest actually existed.
// ============================================================
var hansen = ee.Image('UMD/hansen/global_forest_change_2024_v1_12');
var treeCover2000 = hansen.select('treecover2000');
var forestMask = treeCover2000.gte(25);   // keep pixels with at least 25% tree cover

// ============================================================
// 4. Prepare the final image to display
//    - Mask no‑data pixels (if any) by masking out values < 0 or > 1
//    - Clip to India
//    - Apply the optional forest mask
// ============================================================
var validMask = riskImage.gte(0).and(riskImage.lte(1));   // valid probability range
var displayImage = riskImage
  .updateMask(validMask)          // remove any invalid pixels
  .updateMask(forestMask)          // (optional) comment out if you want all pixels
  .clip(india);

// ============================================================
// 5. Visualization parameters
// ============================================================
var visParams = {
  min: 0,
  max: 1,
  palette: [
    'darkgreen',   // 0.0 – very low risk
    'lightgreen',  // 0.25
    'yellow',      // 0.5
    'orange',      // 0.75
    'red'          // 1.0 – very high risk
  ]
};

// ============================================================
// 6. Add layers to the map
// ============================================================
Map.centerObject(india, 5);
Map.addLayer(displayImage, visParams, 'Forest Loss Risk 2021-2023');

// Add India boundary outline
Map.addLayer(ee.Image().paint(india, 0, 1), {palette: ['black']}, 'India Boundary');

// ============================================================
// 7. Add a legend
// ============================================================
var legend = ui.Panel({
  style: {
    position: 'bottom-left',
    padding: '8px 15px',
    backgroundColor: 'white',
    border: '1px solid black'
  }
});

// Title
legend.add(ui.Label({
  value: 'Forest Loss Risk Probability',
  style: {fontWeight: 'bold', fontSize: '14px', margin: '0 0 4px 0'}
}));

// Create a colour bar
var colorBar = ui.Thumbnail({
  image: ee.Image.pixelLonLat().select(0).multiply(0), // dummy image
  params: {
    bbox: '0,0,1,0.1',
    dimensions: '300x30',
    format: 'png',
    min: 0,
    max: 1,
    palette: visParams.palette
  },
  style: {stretch: 'horizontal', margin: '0px 8px', maxHeight: '24px'}
});
legend.add(colorBar);

// Add min/max labels
var labelPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('horizontal'),
  style: {margin: '0 0 4px 0'}
});
labelPanel.add(ui.Label('0 (low)', {margin: '0 0 0 0'}));
labelPanel.add(ui.Label('1 (high)', {margin: '0 0 0 200px'}));
legend.add(labelPanel);

Map.add(legend);

// ============================================================
// 8. (Optional) Add actual forest loss for 2021–2023 as comparison
//    – this helps validate whether high‑risk areas actually lost forest.
// ============================================================
var lossYear = hansen.select('lossyear');
var loss2021_2023 = lossYear.gte(21).and(lossYear.lte(23)).selfMask().clip(india);
Map.addLayer(loss2021_2023, {palette: ['blue']}, 'Actual Forest Loss 2021-2023', false);