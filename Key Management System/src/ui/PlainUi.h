#ifndef KMS_UI_PLAINUI_H
#define KMS_UI_PLAINUI_H

#include "core/Registry.h"
#include "core/RegistryFile.h"

#include <iosfwd>
#include <string>

namespace kms {

// The original numbered menu, for pipes, scripts and simple consoles.
class PlainUi {
public:
    PlainUi(std::istream& input, std::ostream& output, Registry& registry, Format format);
    int run();

private:
    std::string readLine(const std::string& prompt);
    int readChoice();
    void printKeys(const Employee& employee);

    std::istream& in_;
    std::ostream& out_;
    Registry& registry_;
    Format format_;
};

}  // namespace kms

#endif
