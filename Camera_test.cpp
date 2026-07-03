#include <cstdlib>
#include <iostream>

int runCommand(const char* command) {
    std::cout << "Running: " << command << std::endl;
    return std::system(command);
}

int openCameraPreview() {
    int result = runCommand("rpicam-hello --timeout 0");
    if (result == 0) {
        return 0;
    }

    std::cout << "rpicam-hello did not start. Trying libcamera-hello instead..." << std::endl;
    result = runCommand("libcamera-hello --timeout 0");
    if (result == 0) {
        return 0;
    }

    std::cerr << "Could not open the camera preview." << std::endl;
    std::cerr << "Check that the camera works in the terminal first." << std::endl;
    return 1;
}

int main() {
    std::cout << "Opening Raspberry Pi camera preview." << std::endl;
    std::cout << "Press Ctrl+C to stop it." << std::endl;
    return openCameraPreview();
}
