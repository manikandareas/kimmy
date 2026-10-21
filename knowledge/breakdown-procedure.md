---
title: Prosedur Penanganan Breakdown — SOP Simulasi
version: 1.0
effective_date: 2026-08-01
---
# Prosedur Penanganan Breakdown

## Laporan dan pengamanan
Saat kendaraan tidak dapat beroperasi, pengemudi mengamankan lokasi sesuai prosedur perusahaan dan menghubungi petugas operasional. Petugas mencatat kendaraan, waktu reported_at, awal out_of_service_at, component, symptom, dan severity. Severity memakai low, medium, high, atau critical. Asisten merangkum laporan yang tersedia dan tidak mengubah data operasional. Waktu pelaporan berbeda dari waktu mulai tidak beroperasi.

## Diagnosis dan work order
Symptom adalah keluhan, bukan penyebab terkonfirmasi. confirmed_cause null berarti penyebab belum diketahui. Jangan menyimpulkan akar masalah hanya dari korelasi BBM, maintenance, atau gejala serupa. Work_order_id boleh kosong; jika ada, work order harus milik kendaraan yang sama. Petugas menindaklanjuti diagnosis dan pekerjaan corrective. Waktu returned_to_service_at hanya diisi ketika kendaraan benar-benar kembali beroperasi; null berarti interval belum ditutup.

## Downtime dalam periode
Hitung downtime sebagai irisan interval out_of_service_at hingga returned_to_service_at dengan periode setengah terbuka [start,end). Interval terbuka dibatasi oleh akhir periode pengamatan. Gabungkan interval yang tumpang tindih pada kendaraan yang sama agar durasi tidak dihitung dua kali. Kejadian yang dilaporkan sebelum awal periode tetap dapat menyumbang downtime di dalam periode. Daftar laporan breakdown memakai reported_at; daftar itu berbeda dari himpunan interval penyumbang downtime.

## Depot dan bukti laporan
Riwayat breakdown disajikan per unit. Breakdown dan work order tidak menyimpan snapshot depot pada waktu kejadian. Jika memfilter depot kendaraan kini, beri label current_vehicle_depot dan jangan menyebutnya depot historis. Cantumkan periode pengamatan, metode, coverage, serta referensi tabel/id. Status teknis kini diprioritaskan breakdown ketika interval out-of-service aktif. Tidak ada record bukan bukti tidak pernah terjadi breakdown di luar cakupan dataset.
