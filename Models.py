from typing import List, Tuple, Union

import torch
import torch.nn as nn

import Misc
import ModelParts


class OccupancyNetwork(nn.Module):
    """
    Implementation of an occupancy network for binary classification of a 3D volume
    """

    def __init__(self, number_of_encoding_blocks: int = 5,  # 5,  # Encoding path parameters
                 channels_in_encoding_blocks: List[Tuple[int, int]] =
                 [(1, 32), (32, 32), (32, 64), (64, 64), (64, 8)],
                 # [(1, 64), (64, 64), (64, 128), (128, 128), (128, 8)]
                 kernel_size_encoding: Union[int, List[int]] = 3, stride_encoding: Union[int, List[int]] = 1,
                 padding_encoding: Union[int, List[int]] = 1,
                 activation_encoding: Union[str, List[str]] = 'leaky relu',
                 downsampling_encoding: Union[str, List[str]] =
                 #   ['none', 'averagepool', 'averagepool', 'averagepool', 'averagepool'],
                 ['averagepool', 'averagepool', 'averagepool', 'averagepool', 'none'],
                 downsampling_factor_encoding: Union[int, List[int]] = 2,
                 normalization_encoding: Union[str, List[str]] = 'instancenorm',
                 dropout_rate_encoding: Union[float, List[float]] = 0.0,
                 bias_encoding: Union[bool, List[bool]] = False,
                 number_of_decoding_blocks: int = 5,  # Decoding path parameter
                 channels_in_decoding_blocks: List[Tuple[int, int]] =
                 [(480 + 3, 128), (128, 128), (128, 128), (128, 128), (128, 128)],
                 #  [(180 + 3, 256), (256, 256), (256, 256), (256, 256), (256, 256), (256, 1)],
                 activation_decoding: Union[str, List[str]] = 'leaky relu',
                 normalization_decoding: Union[str, List[str]] = 'cbatchnorm',
                 dropout_rate_decoding: Union[float, List[float]] = [0.0, 0.0, 0.0, 0.0, 0.0],
                 bias_decoding: Union[bool, List[bool]] = True,
                 output_activation: str = 'sigmoid') -> None:
        """
        Constructor method
        :param number_of_encoding_blocks: (int) Number of blocks in encoding path
        :param channels_in_encoding_blocks: (List[Tuple[int]]) Number of input and output channels of each encoding block
        :param kernel_size_encoding: (int, List[int]) Kernel size of each convolution in each encoding block
        :param stride_encoding: (int, List[int]) Stride of each convolution in each encoding block
        :param padding_encoding: (int, List[int]) Padding of each convolution in each encoding block
        :param activation_encoding: (str, List[str]) Activation used in each encoding block
        :param downsampling_encoding: (str, List[str]) Downsampling operation in each encoding block
        :param downsampling_factor_encoding: (int, List[int]) Downsampling factor in each encoding block
        :param normalization_encoding: (str, List[str]) Type of normalization use in each encoding block
        :param dropout_rate_encoding: (float, List[float]) Dropout rate to perform in each encoding block
        :param bias_encoding: (bool, List[bool]) Use bias in each convolution in each encoding block
        :param number_of_decoding_blocks: (int) Number of block in decoding path
        :param channels_in_decoding_blocks: (List[Tuple[int]]) Number of input and output channels of each decoding block
        :param activation_decoding: (str, List[str]) Activation used in each decoding block
        :param normalization_decoding: (str, List[str]) Type of normalization use in each decoding block
        :param dropout_rate_decoding: (float, List[float]) Dropout rate to perform in each decoding block
        :param bias_decoding: (bool, List[bool]) Use bias in each convolution in each decoding block
        :param bias_residual_decoding: (bool, List[bool]) Use bias in residual mapping in each decoding block
        :param output_activation: (str) Type of activation function used for output
        """
        # Call super constructor
        super(OccupancyNetwork, self).__init__()
        # Convert encoding parameters to lists
        channels_in_encoding_blocks = Misc.parse_to_list(channels_in_encoding_blocks, number_of_encoding_blocks,
                                                         'channels in encoding blocks')
        kernel_size_encoding = Misc.parse_to_list(kernel_size_encoding, number_of_encoding_blocks,
                                                  'kernel size encoding')
        stride_encoding = Misc.parse_to_list(stride_encoding, number_of_encoding_blocks,
                                             'stride encoding')
        padding_encoding = Misc.parse_to_list(padding_encoding, number_of_encoding_blocks,
                                              'padding encoding')
        activation_encoding = Misc.parse_to_list(activation_encoding, number_of_encoding_blocks,
                                                 'activation encoding')
        downsampling_encoding = Misc.parse_to_list(downsampling_encoding, number_of_encoding_blocks,
                                                   'downsampling encoding')
        downsampling_factor_encoding = Misc.parse_to_list(downsampling_factor_encoding, number_of_encoding_blocks,
                                                          'downsampling factor encoding')
        normalization_encoding = Misc.parse_to_list(normalization_encoding, number_of_encoding_blocks,
                                                    'normalization encoding')
        dropout_rate_encoding = Misc.parse_to_list(dropout_rate_encoding, number_of_encoding_blocks,
                                                   'dropout rate encoding')
        bias_encoding = Misc.parse_to_list(bias_encoding, number_of_encoding_blocks,
                                           'bias encoding')
        # Convert decoding parameters to lists
        channels_in_decoding_blocks = Misc.parse_to_list(channels_in_decoding_blocks, number_of_decoding_blocks,
                                                         'channels in decoding blocks')
        activation_decoding = Misc.parse_to_list(activation_decoding, number_of_decoding_blocks,
                                                 'activation decoding')
        normalization_decoding = Misc.parse_to_list(normalization_decoding, number_of_decoding_blocks,
                                                    'normalization decoding')
        dropout_rate_decoding = Misc.parse_to_list(dropout_rate_decoding, number_of_decoding_blocks,
                                                   'dropout rate decoding')
        bias_decoding = Misc.parse_to_list(bias_decoding, number_of_decoding_blocks,
                                           'bias decoding')

        # Init encoding blocks
        self.encoding = nn.Sequential(*[ModelParts.VolumeEncoderBlock(
            input_channels=channels_in_encoding_blocks[index][0],
            output_channels=channels_in_encoding_blocks[index][1],
            kernel_size=kernel_size_encoding[index],
            stride=stride_encoding[index],
            padding=padding_encoding[index],
            activation=activation_encoding[index],
            downsampling=downsampling_encoding[index],
            downsampling_factor=downsampling_factor_encoding[index],
            normalization=normalization_encoding[index],
            dropout_rate=dropout_rate_encoding[index],
            bias=bias_encoding[index])
            for index in range(number_of_encoding_blocks)])

        # Init decoding blocks
        self.decoding = nn.ModuleList()
        for index in range(number_of_decoding_blocks):
            self.decoding.append(ModelParts.CoordinatesFullyConnectedBlock(
                input_channels=channels_in_decoding_blocks[index][0],
                output_channels=channels_in_decoding_blocks[index][1],
                activation=activation_decoding[index],
                normalization=normalization_decoding[index],
                dropout_rate=dropout_rate_decoding[index],
                bias=bias_decoding[index]))

        # Init output activation
        self.output_block = nn.Sequential(
            nn.Linear(in_features=channels_in_decoding_blocks[-1][1], out_features=1, bias=True),
            Misc.get_activation(output_activation))

    def forward(self, volume: torch.tensor, coordinates: torch.tensor) -> torch.tensor:
        """
        Forward pass of the occupancy network
        :param volume: (torch.tensor) Input tensor including 3D volume
        :param coordinates: (torch.tensor) Input tensor including coordinates
        :return: (torch.tensor) Output tensor
        """
        # Perform encoding path
        output_encoding = self.encoding(volume)
        # Flatten latent vector for decoding path
        output_encoding_flatten = output_encoding.view(output_encoding.shape[0], -1)
        # Repeat latent vector
        input_decoding = torch.cat((torch.repeat_interleave(output_encoding_flatten,
                                                            int(coordinates.shape[0] / volume.shape[0]), dim=0),
                                    coordinates), dim=1)
        # Perform decoding path
        for index, block in enumerate(self.decoding):
            if index == 0:
                output_decoding = block(input_decoding, output_encoding_flatten.clone())
            else:
                output_decoding = block(output_decoding, output_encoding_flatten.clone())
        # Perform last linear layer + sigmoid activation
        output = self.output_block(output_decoding)
        return output


class OccupancyNetworkNoCat(nn.Module):
    """
    Implementation of an occupancy network for binary classification of a 3D volume with no concatenation of latent tensor
    """

    def __init__(self, number_of_encoding_blocks: int = 5,  # 5,  # Encoding path parameters
                 channels_in_encoding_blocks: List[Tuple[int, int]] =
                 [(1, 64), (64, 64), (64, 64), (64, 64), (64, 8)],
                 #   [(1, 32), (32, 64), (64, 128),(128, 64), (64, 32), (32, 3)],
                 #   [(1, 64), (64, 128), (128, 256),(256, 128), (128, 64), (64, 3)],
                 kernel_size_encoding: Union[int, List[int]] = 3, stride_encoding: Union[int, List[int]] = 1,
                 padding_encoding: Union[int, List[int]] = 1,
                 activation_encoding: Union[str, List[str]] = 'leaky relu',
                 downsampling_encoding: Union[str, List[str]] =
                 #   ['none', 'averagepool', 'averagepool', 'averagepool', 'averagepool'],
                 ['averagepool', 'averagepool', 'averagepool', 'averagepool', 'none'],
                 downsampling_factor_encoding: Union[int, List[int]] = 2,
                 normalization_encoding: Union[str, List[str]] = 'instancenorm',
                 dropout_rate_encoding: Union[float, List[float]] = 0.0,
                 bias_encoding: Union[bool, List[bool]] = False,
                 number_of_decoding_blocks: int = 5,  # Decoding path parameter
                 channels_in_decoding_blocks: List[Tuple[int, int]] =
                 [(3, 128), (128, 128), (128, 128), (128, 128), (128, 128)],
                 #  [(180 + 3, 256), (256, 256), (256, 256), (256, 256), (256, 256), (256, 1)],
                 activation_decoding: Union[str, List[str]] = 'leaky relu',
                 normalization_decoding: Union[str, List[str]] = 'cbatchnorm',
                 dropout_rate_decoding: Union[float, List[float]] = [0.0, 0.0, 0.0, 0.0, 0.0],
                 bias_decoding: Union[bool, List[bool]] = True,
                 output_activation: str = 'sigmoid') -> None:
        """
        Constructor method
        :param number_of_encoding_blocks: (int) Number of blocks in encoding path
        :param channels_in_encoding_blocks: (List[Tuple[int]]) Number of input and output channels of each encoding block
        :param kernel_size_encoding: (int, List[int]) Kernel size of each convolution in each encoding block
        :param stride_encoding: (int, List[int]) Stride of each convolution in each encoding block
        :param padding_encoding: (int, List[int]) Padding of each convolution in each encoding block
        :param activation_encoding: (str, List[str]) Activation used in each encoding block
        :param downsampling_encoding: (str, List[str]) Downsampling operation in each encoding block
        :param downsampling_factor_encoding: (int, List[int]) Downsampling factor in each encoding block
        :param normalization_encoding: (str, List[str]) Type of normalization use in each encoding block
        :param dropout_rate_encoding: (float, List[float]) Dropout rate to perform in each encoding block
        :param bias_encoding: (bool, List[bool]) Use bias in each convolution in each encoding block
        :param number_of_decoding_blocks: (int) Number of block in decoding path
        :param channels_in_decoding_blocks: (List[Tuple[int]]) Number of input and output channels of each decoding block
        :param activation_decoding: (str, List[str]) Activation used in each decoding block
        :param normalization_decoding: (str, List[str]) Type of normalization use in each decoding block
        :param dropout_rate_decoding: (float, List[float]) Dropout rate to perform in each decoding block
        :param bias_decoding: (bool, List[bool]) Use bias in each convolution in each decoding block
        :param bias_residual_decoding: (bool, List[bool]) Use bias in residual mapping in each decoding block
        :param output_activation: (str) Type of activation function used for output
        """
        # Call super constructor
        super(OccupancyNetworkNoCat, self).__init__()
        # Convert encoding parameters to lists
        channels_in_encoding_blocks = Misc.parse_to_list(channels_in_encoding_blocks, number_of_encoding_blocks,
                                                         'channels in encoding blocks')
        kernel_size_encoding = Misc.parse_to_list(kernel_size_encoding, number_of_encoding_blocks,
                                                  'kernel size encoding')
        stride_encoding = Misc.parse_to_list(stride_encoding, number_of_encoding_blocks,
                                             'stride encoding')
        padding_encoding = Misc.parse_to_list(padding_encoding, number_of_encoding_blocks,
                                              'padding encoding')
        activation_encoding = Misc.parse_to_list(activation_encoding, number_of_encoding_blocks,
                                                 'activation encoding')
        downsampling_encoding = Misc.parse_to_list(downsampling_encoding, number_of_encoding_blocks,
                                                   'downsampling encoding')
        downsampling_factor_encoding = Misc.parse_to_list(downsampling_factor_encoding, number_of_encoding_blocks,
                                                          'downsampling factor encoding')
        normalization_encoding = Misc.parse_to_list(normalization_encoding, number_of_encoding_blocks,
                                                    'normalization encoding')
        dropout_rate_encoding = Misc.parse_to_list(dropout_rate_encoding, number_of_encoding_blocks,
                                                   'dropout rate encoding')
        bias_encoding = Misc.parse_to_list(bias_encoding, number_of_encoding_blocks,
                                           'bias encoding')
        # Convert decoding parameters to lists
        channels_in_decoding_blocks = Misc.parse_to_list(channels_in_decoding_blocks, number_of_decoding_blocks,
                                                         'channels in decoding blocks')
        activation_decoding = Misc.parse_to_list(activation_decoding, number_of_decoding_blocks,
                                                 'activation decoding')
        normalization_decoding = Misc.parse_to_list(normalization_decoding, number_of_decoding_blocks,
                                                    'normalization decoding')
        dropout_rate_decoding = Misc.parse_to_list(dropout_rate_decoding, number_of_decoding_blocks,
                                                   'dropout rate decoding')
        bias_decoding = Misc.parse_to_list(bias_decoding, number_of_decoding_blocks,
                                           'bias decoding')

        # Init encoding blocks
        self.encoding = nn.Sequential(*[ModelParts.VolumeEncoderBlock(
            input_channels=channels_in_encoding_blocks[index][0],
            output_channels=channels_in_encoding_blocks[index][1],
            kernel_size=kernel_size_encoding[index],
            stride=stride_encoding[index],
            padding=padding_encoding[index],
            activation=activation_encoding[index],
            downsampling=downsampling_encoding[index],
            downsampling_factor=downsampling_factor_encoding[index],
            normalization=normalization_encoding[index],
            dropout_rate=dropout_rate_encoding[index],
            bias=bias_encoding[index])
            for index in range(number_of_encoding_blocks)])

        # Init decoding blocks
        self.decoding = nn.ModuleList()
        for index in range(number_of_decoding_blocks):
            self.decoding.append(ModelParts.CoordinatesFullyConnectedBlock(
                input_channels=channels_in_decoding_blocks[index][0],
                output_channels=channels_in_decoding_blocks[index][1],
                activation=activation_decoding[index],
                normalization=normalization_decoding[index],
                dropout_rate=dropout_rate_decoding[index],
                bias=bias_decoding[index]))

        # Init output activation
        self.output_block = nn.Sequential(
            nn.Linear(in_features=channels_in_decoding_blocks[-1][1], out_features=1, bias=True),
            Misc.get_activation(output_activation))

    def forward(self, volume: torch.tensor, coordinates: torch.tensor) -> torch.tensor:
        """
        Forward pass of the occupancy network
        :param volume: (torch.tensor) Input tensor including 3D volume
        :param coordinates: (torch.tensor) Input tensor including coordinates
        :return: (torch.tensor) Output tensor
        """
        # Perform encoding path
        output_encoding = self.encoding(volume)
        # Flatten latent vector for decoding path
        output_encoding_flatten = output_encoding.view(output_encoding.shape[0], -1)
        # Perform decoding path
        for index, block in enumerate(self.decoding):
            if index == 0:
                output_decoding = block(coordinates, output_encoding_flatten)
            else:
                output_decoding = block(output_decoding, output_encoding_flatten)
        # Perform last linear layer + sigmoid activation
        output = self.output_block(output_decoding)
        return output


class OccupancyNetworkNoCatCNN(nn.Module):

    def __init__(self, number_of_encoding_blocks: int = 5,  # 5,  # Encoding path parameters
                 channels_in_encoding_blocks: List[Tuple[int, int]] =
                 [(1, 64), (64, 128), (128, 128), (128, 64), (64, 8)],
                 kernel_size_encoding: Union[int, List[int]] = 3, stride_encoding: Union[int, List[int]] = 1,
                 padding_encoding: Union[int, List[int]] = 1,
                 activation_encoding: Union[str, List[str]] = 'leaky relu',
                 downsampling_encoding: Union[str, List[str]] =
                 ['averagepool', 'averagepool', 'averagepool', 'averagepool', 'none'],
                 downsampling_factor_encoding: Union[int, List[int]] = 2,
                 normalization_encoding: Union[str, List[str]] = 'instancenorm',
                 dropout_rate_encoding: Union[float, List[float]] = 0.0,
                 bias_encoding: Union[bool, List[bool]] = False,
                 number_of_decoding_blocks: int = 3,
                 channels_in_decoding_blocks: List[Tuple[int, int]] =
                 [(9, 2), (2, 1), (1, 1)],
                 kernel_size_decoding: Union[int, List[int]] = 3, stride_decoding: Union[int, List[int]] = 1,
                 padding_decoding: Union[int, List[int]] = 1,
                 activation_decoding: Union[str, List[str]] = 'leaky relu',
                 downsampling_decoding: Union[str, List[str]] =
                 ['none', 'none', 'none'],
                 downsampling_factor_decoding: Union[int, List[int]] = 2,
                 normalization_decoding: Union[str, List[str]] = 'none',
                 dropout_rate_decoding: Union[float, List[float]] = 0.0,
                 bias_decoding: Union[bool, List[bool]] = False) -> None:
        # Call super constructor
        super(OccupancyNetworkNoCatCNN, self).__init__()
        # Convert encoding parameters to lists
        channels_in_encoding_blocks = Misc.parse_to_list(channels_in_encoding_blocks, number_of_encoding_blocks,
                                                         'channels in encoding blocks')
        kernel_size_encoding = Misc.parse_to_list(kernel_size_encoding, number_of_encoding_blocks,
                                                  'kernel size encoding')
        stride_encoding = Misc.parse_to_list(stride_encoding, number_of_encoding_blocks,
                                             'stride encoding')
        padding_encoding = Misc.parse_to_list(padding_encoding, number_of_encoding_blocks,
                                              'padding encoding')
        activation_encoding = Misc.parse_to_list(activation_encoding, number_of_encoding_blocks,
                                                 'activation encoding')
        downsampling_encoding = Misc.parse_to_list(downsampling_encoding, number_of_encoding_blocks,
                                                   'downsampling encoding')
        downsampling_factor_encoding = Misc.parse_to_list(downsampling_factor_encoding, number_of_encoding_blocks,
                                                          'downsampling factor encoding')
        normalization_encoding = Misc.parse_to_list(normalization_encoding, number_of_encoding_blocks,
                                                    'normalization encoding')
        dropout_rate_encoding = Misc.parse_to_list(dropout_rate_encoding, number_of_encoding_blocks,
                                                   'dropout rate encoding')
        bias_encoding = Misc.parse_to_list(bias_encoding, number_of_encoding_blocks,
                                           'bias encoding')
        # Convert decoding parameters to lists
        channels_in_decoding_blocks = Misc.parse_to_list(channels_in_decoding_blocks, number_of_decoding_blocks,
                                                         'channels in encoding blocks')
        kernel_size_decoding = Misc.parse_to_list(kernel_size_decoding, number_of_decoding_blocks,
                                                  'kernel size encoding')
        stride_decoding = Misc.parse_to_list(stride_decoding, number_of_decoding_blocks,
                                             'stride encoding')
        padding_decoding = Misc.parse_to_list(padding_decoding, number_of_decoding_blocks,
                                              'padding encoding')
        activation_decoding = Misc.parse_to_list(activation_decoding, number_of_decoding_blocks,
                                                 'activation encoding')
        downsampling_decoding = Misc.parse_to_list(downsampling_decoding, number_of_decoding_blocks,
                                                   'downsampling encoding')
        downsampling_factor_decoding = Misc.parse_to_list(downsampling_factor_decoding, number_of_decoding_blocks,
                                                          'downsampling factor encoding')
        normalization_decoding = Misc.parse_to_list(normalization_decoding, number_of_decoding_blocks,
                                                    'normalization encoding')
        dropout_rate_decoding = Misc.parse_to_list(dropout_rate_decoding, number_of_decoding_blocks,
                                                   'dropout rate encoding')
        bias_decoding = Misc.parse_to_list(bias_decoding, number_of_decoding_blocks,
                                           'bias encoding')

        # Init encoding blocks
        self.encoding = nn.Sequential(*[ModelParts.VolumeEncoderBlock(
            input_channels=channels_in_encoding_blocks[index][0],
            output_channels=channels_in_encoding_blocks[index][1],
            kernel_size=kernel_size_encoding[index],
            stride=stride_encoding[index],
            padding=padding_encoding[index],
            activation=activation_encoding[index],
            downsampling=downsampling_encoding[index],
            downsampling_factor=downsampling_factor_encoding[index],
            normalization=normalization_encoding[index],
            dropout_rate=dropout_rate_encoding[index],
            bias=bias_encoding[index])
            for index in range(number_of_encoding_blocks)])

        # Init input coordinate mapping
        self.coordinate_mapping = nn.Sequential(
            nn.ConvTranspose2d(1, 1, kernel_size=(5, 2), stride=(1, 1), padding=(0, 0)),
            nn.Conv2d(1, 3, kernel_size=(1, 1), stride=(1, 1), padding=(0, 0)))

        # Init decoder blocks
        self.decoding = nn.Sequential(*[ModelParts.VolumeEncoderBlock(
            input_channels=channels_in_decoding_blocks[index][0],
            output_channels=channels_in_decoding_blocks[index][1],
            kernel_size=kernel_size_decoding[index],
            stride=stride_decoding[index],
            padding=padding_decoding[index],
            activation=activation_decoding[index],
            downsampling=downsampling_decoding[index],
            downsampling_factor=downsampling_factor_decoding[index],
            normalization=normalization_decoding[index],
            dropout_rate=dropout_rate_decoding[index],
            bias=bias_decoding[index])
            for index in range(number_of_decoding_blocks)])

        # Init final classification layer
        self.classification = nn.Sequential(nn.Flatten(), nn.Linear(60, 1), nn.Sigmoid())

    def forward(self, volume: torch.tensor, coordinates: torch.tensor) -> torch.Tensor:
        # Perform encoding path
        output_encoding = self.encoding(volume)
        # Map coordinates
        mapped_coordinates = self.coordinate_mapping(coordinates.view(coordinates.shape[0], 1, 1, 3)).unsqueeze(
            dim=1).permute(0, 1, 3, 2, 4)
        # Concat output of encoder and coordinates
        input_decoding = torch.cat((
            torch.repeat_interleave(output_encoding, int(coordinates.shape[0] / volume.shape[0]),
                                    dim=0), mapped_coordinates), dim=1)
        # Perform decoding path
        output_decoding = self.decoding(input_decoding)
        # Perform classification
        classification_output = self.classification(output_decoding)
        return classification_output
