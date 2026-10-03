#ifndef KMS_CORE_REGISTRYFILE_H
#define KMS_CORE_REGISTRYFILE_H

#include "core/Registry.h"

#include <iosfwd>
#include <string>

namespace kms {

// Two on-disk formats.
//
// Classic, the original course format: an employee count, then for each employee a name line
// and a line with their key count and identifiers.
//
//   2
//   Ya Hoo
//   3 AHC102 AHC200 AHC111
//
// Version 2 adds key labels and the activity history, in labelled sections:
//
//   KEY_REGISTRY_V2
//   [keys]
//   AHC102 | Server room
//   [employees]
//   Ya Hoo | AHC102 AHC200 AHC111
//   [history]
//   2026-10-02 14:03 | issue | Ya Hoo | AHC111
//
// Blank lines and lines starting with # are ignored in version 2.
enum class Format { Classic, V2 };

struct ReadResult {
    bool ok = false;
    Format format = Format::Classic;
    std::string error;  // includes the line number when a line is at fault
};

ReadResult readRegistry(std::istream& input, Registry& registry);
bool writeRegistry(std::ostream& output, const Registry& registry, Format format, std::string& error);

ReadResult loadRegistry(const std::string& path, Registry& registry);
bool saveRegistry(const std::string& path, const Registry& registry, Format format, std::string& error);

// Comma-separated export: one row per held key, plus keys on the hook.
std::string toCsv(const Registry& registry);

}  // namespace kms

#endif
