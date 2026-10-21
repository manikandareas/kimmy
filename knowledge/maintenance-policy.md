---
title: Kebijakan Maintenance Armada — SOP Simulasi
version: 1.0
effective_date: 2026-08-01
---
# Kebijakan Maintenance Armada

## Pemeriksaan jadwal dan pekerjaan
Petugas memeriksa work order kendaraan berdasarkan unit_code. Maintenance preventive mengacu pada due_at atau due_odometer_km yang tercatat; jangan mengarang interval servis yang tidak tersedia. Maintenance corrective menangani keluhan atau kerusakan. Status work order adalah open, scheduled, in_progress, completed, atau cancelled. Tampilkan scheduled_at, due_at, dan due_odometer_km jika tersedia. Nilai null berarti informasi belum tersedia, bukan nol atau pekerjaan sudah selesai. Biaya total_cost_idr adalah biaya yang tercatat pada work order, bukan estimasi biaya BBM.

## Status teknis dan kesiapan kendaraan
Status teknis kendaraan dihitung saat query: breakdown jika ada interval out-of-service aktif, kemudian maintenance jika ada work order in_progress, kemudian maintenance_pending jika ada work order open atau scheduled, selain itu operational. Maintenance_pending tidak membuktikan kendaraan berhenti beroperasi. Downtime bersumber dari interval breakdown, bukan selisih waktu work order. Status ini merupakan snapshot dataset kini; histori status teknis lengkap tidak dapat direkonstruksi karena audit perubahan status work order tidak tersedia.

## Bukti penggunaan dan depot
Jam operasi berasal dari engine_on_seconds pada operation_sessions, bukan durasi trip atau durasi sesi. Total lengkap hanya memakai sesi tertutup dengan coverage_status complete dan engine_on_seconds tersedia. Sesi partial, none, atau tanpa angka mesin dilaporkan sebagai keterbatasan; jangan diprorata saat melewati batas periode. Riwayat maintenance didukung per unit. Work order tidak memiliki depot historis; filter depot kendaraan kini harus dilabelkan current_vehicle_depot. Snapshot depot historis tersedia pada trips, fuel_entries, dan operation_sessions saja.

## Analisis dan tindak lanjut
Bandingkan catatan maintenance dengan pengamatan operasi menggunakan periode yang jelas dan referensi tabel/id. Kenaikan estimasi konsumsi setelah servis tidak membuktikan servis menyebabkan kenaikan. Ajukan pemeriksaan teknis dan catat keterbatasan data. Asisten hanya membaca data armada; persetujuan atau pencatatan pekerjaan dilakukan petugas di luar aplikasi demo. Dokumen ini SOP simulasi, bukan bukti pekerjaan telah dilaksanakan.
