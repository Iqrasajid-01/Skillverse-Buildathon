import { useState } from 'react';

export default function ExcelUpload({ onUploadSuccess, onClose }) {
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer?.files;
    if (files && files[0]) {
      await uploadFile(files[0]);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  };

  const uploadFile = async (file) => {
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      setError('Please upload a valid Excel file (.xlsx or .xls)');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8003/api/import/excel', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      // Check if scenario_input was generated
      if (!data.scenario_input) {
        const missing = [];
        if (!data.has_interval_inputs) missing.push('interval_inputs');
        if (!data.has_profile) missing.push('scenario_profile');
        if (!data.has_appliances) missing.push('appliances');
        if (!data.has_energy_assets) missing.push('energy_assets');
        
        if (missing.length > 0) {
          throw new Error(`Excel missing required sheets: ${missing.join(', ')}. Please use the correct template.`);
        }
        throw new Error('Excel uploaded but could not parse scenario data. Check column names.');
      }

      setResult(data);

      if (onUploadSuccess) {
        onUploadSuccess(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload Excel Data
            </h2>
            <button onClick={onClose} className="text-white/80 hover:text-white">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="p-6">
          <div
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all ${
              dragActive
                ? 'border-indigo-500 bg-indigo-50'
                : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="flex flex-col items-center gap-4">
              <div className={`w-16 h-16 rounded-full flex items-center justify-center ${dragActive ? 'bg-indigo-100' : 'bg-gray-100'}`}>
                <svg className={`w-8 h-8 ${dragActive ? 'text-indigo-600' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              
              <div>
                <p className="text-lg font-medium text-gray-700">
                  Drop your Excel file here
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  or click to browse
                </p>
              </div>

              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileSelect}
                className="hidden"
                id="excel-upload"
                disabled={uploading}
              />
              
              <label
                htmlFor="excel-upload"
                className={`px-6 py-2.5 rounded-lg font-medium cursor-pointer transition-all ${
                  uploading
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200'
                }`}
              >
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Uploading...
                  </span>
                ) : (
                  'Select File'
                )}
              </label>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          )}

          {result && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-green-500 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-green-700 font-medium">Upload Successful!</p>
                  <div className="mt-2 text-sm text-green-600">
                    <p>Scenarios: {result.scenarios_count}</p>
                    <p>Total Intervals: {result.total_intervals}</p>
                    {result.date_range && (
                      <p>Date Range: {result.date_range}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium text-gray-700 mb-2">Required Sheets:</h3>
            <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 mb-3">
              <span className="bg-white px-2 py-1 rounded">• scenario_profile</span>
              <span className="bg-white px-2 py-1 rounded">• appliances</span>
              <span className="bg-white px-2 py-1 rounded">• energy_assets</span>
              <span className="bg-white px-2 py-1 rounded">• interval_inputs</span>
              <span className="bg-white px-2 py-1 rounded">• baseline_schedule</span>
            </div>
            <div className="text-xs text-gray-500 mb-3">
              <strong>interval_inputs columns:</strong><br/>
              timestamp, scenario_id, interval_minutes, outdoor_temp, indoor_temp, relative_humidity_pct, heat_index_c, solar_irradiance_w_m2, solar_kw, grid_available, grid_carbon_kgco2_per_kwh, tariff_pkr_per_kwh, tariff_type, occupancy_count, non_cooling_load_kw, ac_capacity_kw, setpoint_temp_c, source_missing_flag
            </div>
            <div className="text-xs text-gray-500 mb-3">
              <strong>baseline_schedule columns:</strong><br/>
              scenario_id, timestamp, baseline_ac_units_on, baseline_ac_setpoint_c, baseline_fan_units_on, baseline_other_cooling_kw
            </div>
            <a
              href="/CoolShift_Template.xlsx"
              download
              className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 underline"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Template
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
