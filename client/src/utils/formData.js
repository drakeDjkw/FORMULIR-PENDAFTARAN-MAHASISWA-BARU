/**
 * Builds FormData to send fields together with a file.
 * data  — ordinary fields ({ full_name: "...", gender: "F" })
 * files — files ({ photo: File }); empty values are skipped,
 *         so editing without choosing a new file keeps the old image.
 */
export function toFormData(data, files = {}) {
  const formData = new FormData();
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) continue;
    formData.append(key, value);
  }
  for (const [key, file] of Object.entries(files)) {
    if (file) formData.append(key, file);
  }
  return formData;
}
