from pathlib import Path
from typing import Tuple
import argparse
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.io import wavfile
import matplotlib.pyplot as plt
import das_generator as generator


def load_audio(file_path: Path, num_repeats: int = 1) -> Tuple[int, np.ndarray]:
    """Load audio file and optionally repeat it to increase length"""
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file '{file_path}' not found")

    fs, audio_data = wavfile.read(file_path)
    audio_data = np.repeat(audio_data[:], num_repeats).astype(np.float64)

    return fs, audio_data


def generate_source_path(
    source_position: np.ndarray,
    movement_type: str,
    len_source_signal: int,
    hop: int,
    centroid: np.ndarray,
) -> Tuple[np.ndarray]:
    """
    Generate source path.

    Parameters:
    -----------
    source_position : np.ndarray
        Initial source position
    movement_type : str
        Type of movement ('line' or 'circle')
    len_source_signal : int
        Length of the source signal
    hop : int
        Number of samples between position updates
    centroid : np.ndarray, optional
        Center position for movements

    Returns:
    --------
    sp_path : np.ndarray
        Source path array of shape (3, len_source_signal)
    """

    # Initialize source path and receiver path arrays
    sp_path = np.zeros((3, len_source_signal))

    # Initialize the source path generation depending on the type of movement
    if movement_type.lower() == "line":
        start_x, start_y, start_z = source_position
        stop_x, stop_y = centroid[0] - 1.0, centroid[1] - 1.0

    elif movement_type.lower() == "circle":
        # Calculate the radius of the circle
        radius = np.linalg.norm(source_position - centroid)

        # Create a unit vector from the center to the start position
        start_vector = source_position - centroid
        start_vector /= np.linalg.norm(start_vector)

        # Compute Euler angles to align start_vector with the x-axis
        vx, vy, vz = start_vector
        theta = -np.arctan2(vz, np.sqrt(vx**2 + vy**2))  # Rotate into xy-plane
        psi = -np.arctan2(vy, vx)  # Rotate around z to align with x-axis
        phi = 0

        # Generate the rotation matrix from the Euler angles
        rotation = R.from_euler("xyz", [phi, theta, psi])

        # Generate the rotation angle step per sample
        angle_step = 2 * np.pi * hop / len_source_signal

    else:
        raise ValueError(f"Unsupported movement type: {movement_type}")

    # Iterating over the length of the input
    for ii in range(0, len_source_signal, hop):
        if movement_type.lower() == "line":
            # Calculate new source position (line movement)
            x_tmp = start_x + (ii * (stop_x - start_x) / len_source_signal)
            y_tmp = start_y + (ii * (stop_y - start_y) / len_source_signal)
            z_tmp = start_z

            sp_new = np.array([x_tmp, y_tmp, z_tmp])

        elif movement_type.lower() == "circle":
            angle = ii / hop * angle_step

            # Construct the coordinates in the rotated frame
            rotated_coords = np.array(
                [radius * np.cos(angle), radius * np.sin(angle), 0]
            )

            # Inverse rotation to go back to the original coordinate system
            original_coords = rotation.inv().apply(rotated_coords)

            sp_new = original_coords + centroid

        else:
            raise ValueError(f"Unsupported movement type: {movement_type}")

        # Store source path
        end_idx = min(ii + hop, len_source_signal)
        sp_path[:, ii:end_idx] = sp_new[:, np.newaxis]

    return sp_path


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DAS Generator Example")
    parser.add_argument(
        "--audio", type=str, default="female_speech.wav", help="Path to audio file"
    )
    parser.add_argument(
        "--repeats", type=int, default=1, help="Number of times to repeat the audio"
    )
    args = parser.parse_args()

    # Load source signal
    audio_path = Path(args.audio)
    fs, source_signal = load_audio(audio_path, args.repeats)
    len_source_signal = len(source_signal)

    # Room dimensions
    room_dimensions = np.array([5.0, 4.0, 3.5])  # (m)

    # Receiver type
    receiver_type = generator.mic_type.omnidirectional

    # Receiver positions
    # receiver_positions = np.array([[2.6, 2.1, 1.5]])
    receiver_positions = np.array([[2.6, 2.1, 1.5], [2.6, 2.3, 1.5]])

    print(f"Audio loaded: {len_source_signal} samples at {fs}Hz")
    print(f"Room dimensions: {room_dimensions}")

    # Calculate the center of gravity (centroid) of the receiver positions
    centroid = np.mean(receiver_positions, axis=0)

    # Source position w.r.t. centroid
    source_offset = np.array([0.75, -0.75, 0])  # Offset from centroid
    source_position = centroid + source_offset

    # Generate source path (moving) receiver paths (static)
    movement_type = "circle"  # Source movement 'line' or 'circle'
    hop = (
        32  # Number of samples between each position update (reduces computation time)
    )
    sp_path = generate_source_path(
        source_position, movement_type, len_source_signal, hop, centroid
    )

    # Plot 3D source path and receiver positions
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    for mm in range(receiver_positions.shape[0]):
        ax.plot(
            receiver_positions[mm, 0],
            receiver_positions[mm, 1],
            receiver_positions[mm, 2],
            "x",
            label=f"Receiver {mm + 1}",
        )
    ax.plot(sp_path[0, :], sp_path[1, :], sp_path[2, :], "r.", label="Source Path")
    ax.set_xlim([0, room_dimensions[0]])
    ax.set_ylim([0, room_dimensions[1]])
    ax.set_zlim([0, room_dimensions[2]])
    ax.set_xlabel("X Axis")
    ax.set_ylabel("Y Axis")
    ax.set_zlabel("Z Axis")
    ax.grid(True)
    ax.set_box_aspect(
        [room_dimensions[0], room_dimensions[1], room_dimensions[2]]
    )  # Aspect ratio according to room dimensions
    plt.legend()

    receiver_signals = generator.generate(
        source_signal,  # Source signal
        c=340,  # Sound velocity (m/s)
        fs=fs,  # Sample frequency (samples/s)
        rp_path=receiver_positions,  # Static receiver positions
        sp_path=sp_path,  # Source positions for each sample
        L=room_dimensions,  # Room dimensions [x y z] (m)
        reverberation_time=0,  # Reverberation time (s)
        nRIR=1024,  # Number of output samples
        mtypes=receiver_type,  # Receiver type
        orientation=[0, 0],  # Orientation of the receiver
    )

    # Check dimensions of input and output signals
    print("Shape source_signal: ", source_signal.shape)
    print("Shape receiver_signals: ", receiver_signals.shape)

    # Plot input and output signals
    t = np.linspace(0, (len(source_signal) - 1) / fs, len(source_signal))

    plt.figure()
    plt.subplot(211)
    plt.plot(t, source_signal)
    plt.title("in(n)")
    plt.xlabel("Time [Seconds]")
    plt.ylabel("Amplitude")

    plt.subplot(212)
    plt.plot(t, receiver_signals)
    plt.title("out(n)")
    plt.xlabel("Time [Seconds]")
    plt.ylabel("Amplitude")

    plt.tight_layout()
    plt.show()

    # Save output signals to a WAV file
    wavfile.write("example_receiver_signals.wav", fs, receiver_signals)


if __name__ == "__main__":
    main()
