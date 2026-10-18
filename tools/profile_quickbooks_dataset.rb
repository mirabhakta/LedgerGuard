#!/usr/bin/env ruby
# frozen_string_literal: true

# Phase 0-only profiler for the sponsor-provided QuickBooks dataset.
# It reads the extracted YAML files and emits a compact JSON summary used by
# docs/DATASET_REPORT.md. It does not normalize or modify the source records.

require "date"
require "json"
require "yaml"

root = File.expand_path(ARGV.fetch(0))
worlds = Dir.glob(File.join(root, "company-*", "rwm-v4", "world-*")).sort
abort "expected 100 company worlds, found #{worlds.length}" unless worlds.length == 100

def load_yaml(path)
  YAML.safe_load(File.read(path), permitted_classes: [Date], aliases: false)
end

def dtype(value)
  case value
  when nil then "null"
  when String then "string"
  when Integer then "integer"
  when Float then "number"
  when TrueClass, FalseClass then "boolean"
  when Array then "array"
  when Hash then "object"
  else value.class.name
  end
end

def percentile(values, fraction)
  return nil if values.empty?

  sorted = values.sort
  sorted[((sorted.length - 1) * fraction).round]
end

def sample_value(value)
  case value
  when Array
    return [] if value.empty?
    first = value.first
    first.is_a?(Hash) ? [sample_value(first)] : value.first(3)
  when Hash
    value.transform_values { |nested| sample_value(nested) }
  else
    value
  end
end

first_world = worlds.first
families = Dir.glob(File.join(first_world, "**", "*.yaml"))
              .map { |path| path.delete_prefix("#{first_world}/") }
              .sort

profiles = families.map do |relative_path|
  documents = worlds.map do |world|
    [File.basename(world.split("/rwm-v4/").first), load_yaml(File.join(world, relative_path))]
  end

  row_oriented = documents.all? { |_company_id, document| document.is_a?(Array) }
  rows = if row_oriented
           documents.flat_map do |company_id, document|
             document.map { |row| [company_id, row] }
           end
         else
           documents
         end

  counts = documents.map do |_company_id, document|
    document.is_a?(Array) ? document.length : 1
  end

  hashes = rows.map(&:last).select { |row| row.is_a?(Hash) }
  columns = hashes.flat_map(&:keys).uniq.sort.map do |column|
    values = hashes.map { |row| row.key?(column) ? row[column] : nil }
    types = values.map { |value| dtype(value) }.uniq.sort
    null_count = values.count(&:nil?)
    {
      "name" => column,
      "dtype" => types.join(" | "),
      "null_count" => null_count,
      "denominator" => values.length,
      "null_rate" => values.empty? ? nil : (null_count.to_f / values.length)
    }
  end

  samples = rows.first(3).map do |company_id, row|
    {
      "company_id" => company_id,
      "record" => sample_value(row)
    }
  end

  embedded_rows = if !row_oriented && relative_path.start_with?("reports/")
                    documents.sum do |_company_id, document|
                      document.fetch("rows", []).length
                    end
                  end

  {
    "path" => relative_path,
    "shape" => row_oriented ? "record array" : "document object",
    "files" => documents.length,
    "rows_total" => counts.sum,
    "files_nonempty" => counts.count(&:positive?),
    "rows_min" => counts.min,
    "rows_median" => percentile(counts, 0.5),
    "rows_max" => counts.max,
    "embedded_rows_total" => embedded_rows,
    "column_count" => columns.length,
    "columns" => columns,
    "samples" => samples
  }
end

index_rows = JSON.parse(File.read(File.join(root, "index.json")))
index_columns = index_rows.flat_map(&:keys).uniq.sort.map do |column|
  values = index_rows.map { |row| row.key?(column) ? row[column] : nil }
  null_count = values.count(&:nil?)
  {
    "name" => column,
    "dtype" => values.map { |value| dtype(value) }.uniq.sort.join(" | "),
    "null_count" => null_count,
    "denominator" => values.length,
    "null_rate" => null_count.to_f / values.length
  }
end

output = {
  "world_count" => worlds.length,
  "archive_file_count" => Dir.glob(File.join(root, "**", "*"), File::FNM_DOTMATCH).count { |path| File.file?(path) },
  "index" => {
    "rows_total" => index_rows.length,
    "column_count" => index_columns.length,
    "columns" => index_columns,
    "samples" => index_rows.first(3).map { |row| sample_value(row) }
  },
  "families" => profiles
}

puts JSON.pretty_generate(output)
