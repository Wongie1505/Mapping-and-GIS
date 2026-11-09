// Check: is 2025 rainfall in Kasungu normal? Compare to the 1991-2020 average.
// Prints stats and a chart in the Console. NO exports, nothing to run in Tasks.

// Import roi
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation');

// Annual total (mm) image for each year 1991-2025
function annual(y) {
  y = ee.Number(y);
  var s = ee.Date.fromYMD(y, 1, 1);
  return chirps.filterDate(s, s.advance(1, 'year')).sum()
    .rename('P').set('year', y);
}
var annualCol = ee.ImageCollection(ee.List.sequence(1991, 2025).map(annual));

var meanOpts = {reducer: ee.Reducer.mean(), geometry: roi, scale: 5566, maxPixels: 1e9};

// 1. District-mean annual rainfall per year (chart)
var yearly = annualCol.map(function (img) {
  return ee.Feature(null, {year: img.get('year'),
                           P: img.reduceRegion(meanOpts).get('P')});
});
print(ui.Chart.feature.byFeature(yearly, 'year', 'P')
  .setChartType('ColumnChart')
  .setOptions({title: 'Kasungu annual rainfall (CHIRPS, district mean)',
               vAxis: {title: 'mm'}, hAxis: {title: 'Year'}, legend: 'none'}));

// 2. 1991-2020 normal vs 2025
var normal = annualCol.filter(ee.Filter.rangeNumber('year', 1991, 2020)).mean();
var y2025 = ee.Image(annualCol.filter(ee.Filter.eq('year', 2025)).first());

var normalMean = ee.Number(normal.reduceRegion(meanOpts).get('P'));
var p2025Mean = ee.Number(y2025.reduceRegion(meanOpts).get('P'));
print('1991-2020 normal, district mean (mm):', normalMean);
print('2025, district mean (mm):', p2025Mean);
print('2025 vs normal (%):', p2025Mean.subtract(normalMean).divide(normalMean).multiply(100));

// 3. Pixel range, comparable to your Spyder output (min / mean / max)
var statOpts = {reducer: ee.Reducer.minMax().combine(ee.Reducer.mean(), '', true),
                geometry: roi, scale: 5566, maxPixels: 1e9};
print('Normal 1991-2020 pixel stats (mm):', normal.reduceRegion(statOpts));
print('2025 pixel stats (mm):', y2025.reduceRegion(statOpts));